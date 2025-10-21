# app/pages/registry.py

from __future__ import annotations

import importlib
import json
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, Union

from PySide6.QtWidgets import QWidget

# ============================================================
#  Normalização de rotas
# ============================================================

def _normalize_route(route: str) -> str:
    # normaliza rota para deduplicação e navegação estáveis
    return (route or "").strip().replace("\\", "/").replace(" ", "-").lower()

# ============================================================
#  Data Model
# ============================================================

@dataclass(frozen=True)
class PageSpec:
    route: str
    label: str
    sidebar: bool
    order: int
    factory: Callable[..., QWidget]

    def is_valid(self) -> bool:
        return bool(self.route and callable(self.factory))


# ============================================================
#  Helpers internos
# ============================================================

def _normalize(specs: List[PageSpec]) -> List[PageSpec]:
    """Remove duplicatas por route, ordena por (order, label) e filtra inválidos."""
    by_route: dict[str, PageSpec] = {}
    for spec in specs:
        if not isinstance(spec, PageSpec):
            continue
        if not spec.is_valid():
            print(f"[WARN] Ignorando PageSpec inválida: {spec}")
            continue
        by_route[spec.route] = spec  # último vence
    out = list(by_route.values())
    out.sort(key=lambda s: (getattr(s, "order", 1000), s.label or s.route))
    return out


def _safe_import(module_name: str) -> Any | None:
    try:
        return importlib.import_module(module_name)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Falha ao importar módulo '{module_name}': {e}")
        return None


def _infer_route_from_module_name(module_name: str) -> str:
    last = module_name.split(".")[-1]
    if last.endswith("_page"):
        last = last[:-5]
    return last.replace("_", "-")  # rota amigável


def _discover_from_module(module) -> List[PageSpec]:
    specs: List[PageSpec] = []
    if not module:
        return specs

    factory = getattr(module, "build", None)
    if not callable(factory):
        return specs  # sem build, não é página

    # defaults por inferência
    route = _infer_route_from_module_name(getattr(module, "__name__", "page"))
    label = route
    sidebar = True
    order = 1000

    # 1) se houver PAGE dict, usa-o
    meta = getattr(module, "PAGE", None)
    if isinstance(meta, dict):
        route = meta.get("route", route)
        label = meta.get("label", label)
        sidebar = meta.get("sidebar", sidebar)
        order = meta.get("order", order)
    else:
        # 2) senão, tenta as constantes
        route = getattr(module, "ROUTE", getattr(module, "route", route))
        label = getattr(module, "LABEL", getattr(module, "label", label))
        sidebar = getattr(module, "SIDEBAR", getattr(module, "sidebar", sidebar))
        order = getattr(module, "ORDER", getattr(module, "order", order))

    route = _normalize_route(route)

    try:
        specs.append(PageSpec(route=route, label=label, sidebar=bool(sidebar), order=int(order), factory=factory))
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Erro ao extrair PageSpec de módulo {getattr(module, '__name__', module)}: {e}")

    return specs


def _resolve_factory(module_name: str, func_name: str) -> Callable[..., QWidget] | None:
    mod = _safe_import(module_name)
    if not mod:
        return None
    fn = getattr(mod, func_name, None)
    if callable(fn):
        return fn
    print(f"[WARN] Função '{func_name}' não encontrada em módulo '{module_name}'.")
    return None


def _try_infer_module_from_route(route: str, base_pkg: str = "app.pages") -> list[str]:
    dotted = route.replace("/", ".").replace("-", "_")
    cands = [
        f"{base_pkg}.{dotted}_page",
        f"{base_pkg}.{dotted}",
    ]
    # variação simples: rota sem pontos no final
    if "." not in dotted:
        cands.extend([f"{base_pkg}.{route}_page", f"{base_pkg}.{route}"])
    return cands


# ============================================================
#  Manifest loader (suporta vários formatos)
# ============================================================

JsonLike = Union[dict, list, str, int, float, bool, None]


def _coerce_manifest_items(data: JsonLike) -> List[dict]:
    items: List[dict] = []

    # Caso mais comum: lista
    if isinstance(data, list):
        for it in data:
            if isinstance(it, dict):
                items.append(it)
            elif isinstance(it, str):
                # string pode ser "module:function" OU "module"
                if ":" in it:
                    items.append({"factory": it})
                else:
                    items.append({"module": it, "factory": "build"})
            else:
                print(f"[WARN] Item de manifesto ignorado (tipo não suportado em lista): {type(it).__name__}")
        return items

    # Objeto único
    if isinstance(data, dict):
        # Heurística: se tem chaves 'route' ou 'factory', é um único item
        if any(k in data for k in ("route", "factory", "module", "label", "sidebar", "order")):
            return [data]
        # Mapa de rotas:
        # { "home": "app.pages.home_page:build", "settings": {"module":"...", "factory":"build"} }
        for route, spec in data.items():
            if isinstance(spec, str):
                if ":" in spec:
                    items.append({"route": route, "factory": spec})
                else:
                    items.append({"route": route, "module": spec, "factory": "build"})
            elif isinstance(spec, dict):
                obj = {"route": route}
                obj.update(spec)
                items.append(obj)
            else:
                print(f"[WARN] Valor de rota inválido no manifesto: route={route} type={type(spec).__name__}")
        return items

    # Qualquer outra coisa (ex.: lista de palavras ["route","label",...]): ignorar e avisar
    print("[ERRO] Formato de manifesto inválido; esperado lista/objeto JSON.")
    return []


def load_from_manifest(manifest_path: Path) -> List[PageSpec]:
    specs: List[PageSpec] = []
    if not manifest_path.exists():
        print(f"[INFO] Manifesto não encontrado: {manifest_path}")
        return specs

    try:
        raw = manifest_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao ler manifesto de páginas: {e}")
        return specs

    items = _coerce_manifest_items(data)

    for item in items:
        try:
            route = item.get("route", "")
            label = item.get("label", route or None)
            sidebar = bool(item.get("sidebar", True))
            order = int(item.get("order", 1000))

            factory: Callable[..., QWidget] | None = None

            # Prioridade 1: formato novo "module:function" em item["factory"]
            factory_ref = item.get("factory")
            module_name = item.get("module")

            if isinstance(factory_ref, str) and ":" in factory_ref:
                mod_name, func_name = factory_ref.split(":", 1)
                factory = _resolve_factory(mod_name, func_name)

                # Se route vazio, inferir a partir do módulo
                if not route:
                    route = _infer_route_from_module_name(mod_name)

            elif isinstance(factory_ref, str):
                # "build" ou outro nome de função
                func_name = factory_ref

                # 1) Se veio 'module', usar
                if module_name:
                    factory = _resolve_factory(module_name, func_name)
                    if not route:
                        route = _infer_route_from_module_name(module_name)

                # 2) Se não veio módulo, tentar deduzir pelo route
                if not factory:
                    if not route:
                        print(f"[WARN] Item do manifesto com 'factory'='{factory_ref}' mas sem 'module' e sem 'route'. Ignorando.")
                        continue
                    for cand in _try_infer_module_from_route(route):
                        factory = _resolve_factory(cand, func_name)
                        if factory:
                            break

                if not factory:
                    print(f"[WARN] Factory inválida em manifesto: '{factory_ref}' (rota='{route or '?'}'). "
                          f"Informe 'module' ou use 'module:function'.")
                    continue

            elif module_name:
                # módulo sem 'factory' → assumir 'build'
                factory = _resolve_factory(module_name, "build")
                if not route:
                    route = _infer_route_from_module_name(module_name)

            else:
                print(f"[WARN] Item de manifesto sem 'factory'/'module' utilizáveis: {item}")
                continue

            route = _normalize_route(route)

            if not label:
                label = route

            specs.append(PageSpec(route=route, label=label, sidebar=sidebar, order=order, factory=factory))

        except Exception as e:  # noqa: BLE001
            print(f"[WARN] Falha ao processar item do manifesto {item}: {e}")

    return _normalize(specs)


# ============================================================
#  Auto-discovery de páginas (app.pages.*)
# ============================================================

def discover_pages(package: str = "app.pages") -> List[PageSpec]:
    specs: List[PageSpec] = []
    try:
        pkg = importlib.import_module(package)
        for _, module_name, _ in pkgutil.iter_modules(pkg.__path__, f"{package}."):
            module = _safe_import(module_name)
            if not module:
                continue
            found = _discover_from_module(module)
            if not found:
                last = module_name.split(".")[-1]
                looks_like_page = last.endswith("_page") or last in {"home", "settings", "about", "dashboard"}
                if looks_like_page and not callable(getattr(module, "build", None)):
                    print(f"[INFO] Módulo '{module_name}' não expõe build(...).")
            specs.extend(found)
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Descoberta automática de páginas falhou: {e}")

    return _normalize(specs)

# ============================================================
#  API pública
# ============================================================

def get_all_pages(manifest_path: Optional[Path] = None) -> List[PageSpec]:
    manifest_specs = load_from_manifest(manifest_path) if manifest_path and manifest_path.exists() else []
    auto_specs = discover_pages()
    by_route = {s.route: s for s in auto_specs}
    for s in manifest_specs:
        by_route[s.route] = s
    return _normalize(list(by_route.values()))


# ============================================================
#  CLI rápido (debug)
# ============================================================

if __name__ == "__main__":
    print("🔍 Descobrindo páginas em app.pages...")
    found = discover_pages()
    for s in found:
        print(f" - {s.route:20} | label={s.label:20} | sidebar={s.sidebar} | order={s.order}")
