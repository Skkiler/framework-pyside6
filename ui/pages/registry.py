# ui/pages/registry.py

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Callable, List, Optional, Any, Dict, Tuple

from PySide6.QtWidgets import QWidget
try:
    # disponível no Py3.8+
    from typing import Protocol  # type: ignore
except Exception:  # pragma: no cover
    class Protocol:  # fallback bobo
        pass


@dataclass
class PageSpec:
    route: str
    label: str
    sidebar: bool
    order: int
    factory: Callable[..., QWidget]


# ---------- helpers seguros ----------

def _is_protocol(cls: Any) -> bool:
    """True se for typing.Protocol (ou derivado)."""
    try:
        return inspect.isclass(cls) and issubclass(cls, Protocol)
    except Exception:
        return False

def _is_qwidget_subclass(obj: Any) -> bool:
    """True se obj é uma classe que herda de QWidget (e não é Protocol)."""
    try:
        return inspect.isclass(obj) and issubclass(obj, QWidget) and not _is_protocol(obj)
    except Exception:
        return False

def _safe_import(modname: str):
    return importlib.import_module(modname)

def _get_page_meta(mod) -> Optional[Dict[str, Any]]:
    PAGE = getattr(mod, "PAGE", None)
    if not isinstance(PAGE, dict):
        return None
    # defaults
    return {
        "route":   PAGE.get("route") or getattr(mod, "__name__", "page"),
        "label":   PAGE.get("label") or PAGE.get("route") or "Página",
        "sidebar": bool(PAGE.get("sidebar", True)),
        "order":   int(PAGE.get("order", 999)),
    }

def _resolve_factory(mod) -> Optional[Callable[..., QWidget]]:
    """
    Política:
      1) Se houver função module-level `build(task_runner=None, theme_service=None)`, usamos ela.
      2) Senão, se existir uma classe QWidget principal (ex.: HomePage, SettingsPage), criamos uma
         fábrica que instancia essa classe (passando kwargs somente se suportados).
    """
    # 1) build() explícito
    build_fn = getattr(mod, "build", None)
    if callable(build_fn):
        return build_fn

    # 2) primeira classe QWidget "pública" encontrada
    candidates: List[type] = []
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if name.startswith("_"):
            continue
        if _is_qwidget_subclass(obj):
            # evita classes internas do PySide / metaclasses etc.
            if obj.__module__ == mod.__name__:
                candidates.append(obj)

    if not candidates:
        return None

    cls = candidates[0]

    def _factory(**kwargs) -> QWidget:
        sig = inspect.signature(cls)
        # mantém apenas kwargs aceitos pela __init__
        use = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return cls(**use) if use else cls()

    return _factory


# ---------- carregadores ----------

def discover_pages(package: str = "ui.pages") -> List[PageSpec]:
    """
    Auto-descoberta: varre ui.pages.*, importa módulos, lê PAGE e build/cls.
    Ignora qualquer módulo sem PAGE ou sem fábrica válida.
    """
    specs: List[PageSpec] = []
    pkg = importlib.import_module(package)
    for _, subname, ispkg in pkgutil.iter_modules(pkg.__path__, package + "."):
        if ispkg:
            # p.ex. ui.pages.admin.* – pode ter subpacotes; importe também
            try:
                subpkg = importlib.import_module(subname)
            except Exception:
                continue
            # módulos dentro do subpacote
            for _, submodname, _ in pkgutil.iter_modules(subpkg.__path__, subname + "."):
                _try_collect(submodname, specs)
        else:
            _try_collect(subname, specs)

    # ordena pela chave 'order'
    specs.sort(key=lambda s: (s.order, s.label.lower()))
    return specs


def _try_collect(modname: str, out_specs: List[PageSpec]) -> None:
    try:
        mod = _safe_import(modname)
    except Exception:
        return

    meta = _get_page_meta(mod)
    if not meta:
        return

    factory = _resolve_factory(mod)
    if not callable(factory):
        # sem fábrica válida -> ignora
        return

    out_specs.append(
        PageSpec(
            route=meta["route"],
            label=meta["label"],
            sidebar=meta["sidebar"],
            order=meta["order"],
            factory=factory,
        )
    )


def load_from_manifest(manifest_path: str) -> List[PageSpec]:
    """
    Lê um JSON/YAML (você quem define) e monta PageSpecs em ordem.
    Para já, mantive por compatibilidade com teu fluxo anterior — opcional usar.
    O formato esperado por item:
      {"module": "ui.pages.home_page", "route": "home", "label": "Início",
       "sidebar": true, "order": 1, "factory": "build"}
    """
    import json
    from pathlib import Path

    p = Path(manifest_path)
    if not p.exists():
        return []

    raw = json.loads(p.read_text(encoding="utf-8"))
    specs: List[PageSpec] = []
    for item in raw:
        try:
            mod = _safe_import(item["module"])
            meta = {
                "route":   item.get("route") or getattr(mod, "PAGE", {}).get("route"),
                "label":   item.get("label") or getattr(mod, "PAGE", {}).get("label", "Página"),
                "sidebar": bool(item.get("sidebar", True)),
                "order":   int(item.get("order", 999)),
            }
            fac_name = item.get("factory") or "build"
            fac = getattr(mod, fac_name, None)
            if not callable(fac):
                # fallback: tenta class QWidget
                fac = _resolve_factory(mod)
            if not callable(fac):
                raise RuntimeError(f"Factory '{fac_name}' não encontrada/Inválida em {item['module']}")
            specs.append(PageSpec(
                route=meta["route"],
                label=meta["label"],
                sidebar=meta["sidebar"],
                order=meta["order"],
                factory=fac
            ))
        except Exception as e:
            # em produção, logue – aqui só ignora entrada ruim
            continue

    specs.sort(key=lambda s: (s.order, s.label.lower()))
    return specs
