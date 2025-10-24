from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
import json
from datetime import datetime
import importlib


# === utils de nome ===
def to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name.strip())
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return re.sub(r"[\W]+", "_", s2).lower().strip("_")


def to_camel(name: str) -> str:
    parts = re.split(r"[\W_]+", name.strip())
    return "".join(p.capitalize() for p in parts if p)


# === paths ===
def repo_root() -> Path:
    # ui/ is this file's parent; repo is one level up
    return Path(__file__).resolve().parents[1]


def app_dir() -> Path:
    return repo_root() / "app"


def pages_dir() -> Path:
    return app_dir() / "pages"


def assets_dir() -> Path:
    return app_dir() / "assets"


def manifest_path() -> Path:
    return assets_dir() / "pages_manifest.json"


# === templates ===
PAGE_TEMPLATE = """# Auto-gerado por ui.cli em {now}
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame

PAGE = {{
    "route": "{route}",
    "label": "{label}",
    "sidebar": {sidebar},
    "order": {order},
}}

class {class_name}(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QFrame()
        container.setObjectName("PageContainer")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Página: {label}"))
        lay.addStretch(1)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

    # Hook de ciclo de vida (opcional)
    def on_route(self, params: dict | None = None):
        pass

def build(task_runner=None, theme_service=None) -> QWidget:
    return {class_name}(task_runner=task_runner, theme_service=theme_service)
"""

EXAMPLES_TEMPLATE = """# Auto-gerado por ui.cli (exemplos) em {now}
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout
from ui.widgets.buttons import Controls
from ui.widgets.async_button import AsyncTaskButton
from ui.widgets.toast import show_toast, show_action_toast, ProgressToast

PAGE = {{
    "route": "examples",
    "label": "Exemplos",
    "sidebar": True,
    "order": 900,
}}

class ExamplesPage(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(14,14,14,14); root.setSpacing(12)
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        wrap = QFrame(); lv = QVBoxLayout(wrap); lv.setContentsMargins(0,0,0,0); lv.setSpacing(10)

        lv.addWidget(QLabel("Botões (Controls.Button)"))
        row = QHBoxLayout(); row.setSpacing(8)
        b1 = Controls.Button("Primário", size_preset="md"); b1.setProperty("variant","primary"); row.addWidget(b1)
        b2 = Controls.Button("Padrão", size_preset="md"); row.addWidget(b2)
        b3 = Controls.Button("Chip", size_preset="sm"); b3.setProperty("variant","chip"); row.addWidget(b3)
        row.addStretch(1); lv.addLayout(row)

        lv.addWidget(QLabel("AsyncTaskButton"))
        ab = AsyncTaskButton("Executar tarefa")
        def _run():
            import time; time.sleep(1.0); return True
        ab.set_worker(_run)
        ab.succeeded.connect(lambda *_: show_toast(self, "Tarefa OK", kind="ok"))
        ab.failed.connect(lambda *_: show_toast(self, "Tarefa falhou", kind="error"))
        lv.addWidget(ab)

        lv.addWidget(QLabel("Toasts"))
        lv.addWidget(Controls.Button("Toast simples", size_preset="sm", clicked=lambda: show_toast(self, "Ação ok")))

        def _toast_action():
            show_action_toast(self, "Exportação", "Arquivo pronto.", kind="ok",
                              actions=[{"label":"Abrir pasta","command":"abrir_pasta","payload":{}}], persist=True)
        lv.addWidget(Controls.Button("Toast com ação", size_preset="sm", clicked=_toast_action))

        def _toast_progress():
            pt = ProgressToast.start(self, "Processando...", kind="info", cancellable=True)
            for i in range(1, 6):
                from time import sleep; sleep(0.2); pt.update(i, 5)
            pt.finish(True, "Concluído")
        lv.addWidget(Controls.Button("Toast progresso", size_preset="sm", clicked=_toast_progress))

        lv.addStretch(1)
        scroll.setWidget(wrap); root.addWidget(scroll, 1)

def build(task_runner=None, theme_service=None) -> QWidget:
    return ExamplesPage(task_runner=task_runner, theme_service=theme_service)
"""


# === manifest helpers ===
def _manifest_load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")) or []
    except Exception:
        return []


def _manifest_save(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _manifest_upsert_item(items: list[dict], item: dict) -> list[dict]:
    by_route = {it.get("route"): it for it in items if isinstance(it, dict) and it.get("route")}
    by_route[item.get("route")] = item
    out = list(by_route.values())
    out.sort(key=lambda d: (int(d.get("order", 1000)), d.get("label") or d.get("route")))
    return out


# === discovery: import app.pages.* e extrair PAGE/build ===
def discover_page_specs() -> list[dict]:
    specs: list[dict] = []
    root = pages_dir()
    if not root.exists():
        return specs

    if str(repo_root()) not in sys.path:
        sys.path.insert(0, str(repo_root()))

    for py in sorted(root.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        rel = py.relative_to(app_dir()).with_suffix("")  # pages/foo/bar
        parts = [p for p in rel.parts]
        parts[0] = "pages"  # app/pages -> app.pages
        mod_name = "app." + ".".join(parts)
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        route = None; label = None; sidebar = True; order = 1000
        if isinstance(getattr(mod, "PAGE", None), dict):
            md = mod.PAGE
            route = md.get("route")
            label = md.get("label")
            sidebar = bool(md.get("sidebar", True))
            order = int(md.get("order", 1000))
        # fallback: inferir a partir do nome
        if not route:
            last = py.stem
            if last.endswith("_page"):
                last = last[:-5]
            route = last.replace("_", "-")
        if not label:
            label = route
        factory = None
        if callable(getattr(mod, "build", None)):
            factory = f"{mod_name}:build"
        if factory:
            specs.append({
                "route": str(route).lower(),
                "label": label,
                "sidebar": sidebar,
                "order": order,
                "factory": factory,
            })
    specs.sort(key=lambda d: (int(d.get("order", 1000)), d.get("label") or d.get("route")))
    return specs


# === commands ===
def cmd_new_page(args):
    pdir = pages_dir(); pdir.mkdir(parents=True, exist_ok=True)
    class_name = to_camel(args.name) + "Page"
    route = (args.route or to_snake(args.name)).replace("\\", "/").strip("/")
    label = args.label or args.name
    order = int(args.order)
    sidebar = bool(args.sidebar)

    filename = f"{route.replace('/', '_')}_page.py"
    target = pdir / filename
    if target.exists() and not args.force:
        print(f"[ERRO] Arquivo já existe: {target}\nUse --force para sobrescrever.")
        sys.exit(2)

    content = PAGE_TEMPLATE.format(
        now=datetime.now().isoformat(timespec='seconds'),
        route=route, label=label, order=order, sidebar="True" if sidebar else "False", class_name=class_name
    )
    target.write_text(content, encoding="utf-8")

    # manifest: upsert
    man = manifest_path(); items = _manifest_load(man)
    items = _manifest_upsert_item(items, {
        "route": route,
        "label": label,
        "sidebar": sidebar,
        "order": order,
        "factory": f"app.pages.{target.stem}:build",
    })
    _manifest_save(man, items)

    print(f"[OK] Página criada: {target}")
    print(f" - Rota: {route}")
    print(f" - Classe: {class_name}")
    print(f" - Manifesto atualizado: {man}")


def cmd_new_subpage(args):
    parent = (args.parent or "").strip("/")
    if not parent:
        print("[ERRO] Informe --parent com a rota da página pai (ex.: home)")
        sys.exit(2)
    name = args.name
    route_tail = (args.route or to_snake(name)).replace("\\", "/").strip("/")
    full_route = f"{parent}/{route_tail}"
    args.route = full_route
    return cmd_new_page(args)


def cmd_scaffold_examples(args):
    pdir = pages_dir(); pdir.mkdir(parents=True, exist_ok=True)
    target = pdir / "examples_widgets_page.py"
    if target.exists() and not args.force:
        print(f"[ERRO] Arquivo já existe: {target} (--force para sobrescrever)")
        sys.exit(2)
    target.write_text(EXAMPLES_TEMPLATE.format(now=datetime.now().isoformat(timespec='seconds')), encoding="utf-8")

    # add to manifest
    man = manifest_path(); items = _manifest_load(man)
    items = _manifest_upsert_item(items, {
        "route": "examples",
        "label": "Exemplos",
        "sidebar": True,
        "order": 900,
        "factory": "app.pages.examples_widgets_page:build",
    })
    _manifest_save(man, items)
    print(f"[OK] Página de exemplos criada e manifesto atualizado: {target}")


def cmd_manifest_update(args):
    specs = discover_page_specs()
    man = manifest_path()
    _manifest_save(man, specs)
    print(f"[OK] Manifesto reescrito com {len(specs)} entradas: {man}")


def _safe_remove(p: Path):
    try:
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            for sub in p.rglob('*'):
                if sub.is_file():
                    sub.unlink()
            for sub in sorted(p.glob('**/*'), reverse=True):
                if sub.exists() and sub.is_dir():
                    try:
                        sub.rmdir()
                    except Exception:
                        pass
            p.rmdir()
    except Exception:
        pass


def cmd_clean_pages(args):
    pdir = pages_dir()
    # Remover páginas pré-programadas
    targets = [
        pdir / "home_page.py",
        pdir / "notificacoes.py",   # opcional
        pdir / "settings.py",       # opcional
        pdir / "theme_editor.py",   # opcional
        pdir / "subpages" / "guia_rapido_page.py",
        pdir / "subpages",
    ]
    for t in targets:
        _safe_remove(t)

    # Criar home vazia
    ns = argparse.Namespace(name="Home", route="home", label="Início", order=0, sidebar=True, force=True, parent=None)
    cmd_new_page(ns)

    # Limpar manifesto para manter home (ou reconstruir)
    if args.rebuild_manifest:
        cmd_manifest_update(args)
    else:
        man = manifest_path(); items = _manifest_load(man)
        def keep(it: dict) -> bool:
            r = (it or {}).get("route", "")
            return r in {"home"}
        items = [it for it in items if keep(it)] or [{
            "route": "home",
            "label": "Início",
            "sidebar": True,
            "order": 0,
            "factory": "app.pages.home_page:build",
        }]
        _manifest_save(man, items)
        print(f"[OK] Manifesto limpo: {man}
")


def build_parser():
    p = argparse.ArgumentParser(prog="ui-cli", description="Ferramentas de DX do framework UI.")
    sub = p.add_subparsers(dest="command", required=True)

    # new
    sp = sub.add_parser("new", help="Gerar artefatos (páginas, etc.)")
    ssub = sp.add_subparsers(dest="artifact", required=True)

    sp_page = ssub.add_parser("page", help="Criar nova página em app/pages")
    sp_page.add_argument("name", help="Nome lógico da página (ex.: Relatorios, ConfigAvancada)")
    sp_page.add_argument("--route", help="Rota (default: nome em snake-case)")
    sp_page.add_argument("--label", help="Rótulo da sidebar (default: name)")
    sp_page.add_argument("--order", default="999", help="Ordem na sidebar (default: 999)")
    sp_page.add_argument("--sidebar", action="store_true", help="Exibir na sidebar")
    sp_page.add_argument("--force", action="store_true", help="Sobrescrever arquivo existente")
    sp_page.set_defaults(func=cmd_new_page)

    sp_sub = ssub.add_parser("subpage", help="Criar subpágina vinculada a uma rota pai")
    sp_sub.add_argument("name", help="Nome lógico da subpágina")
    sp_sub.add_argument("--parent", required=True, help="Rota pai (ex.: home)")
    sp_sub.add_argument("--route", help="Parte final da rota (default: nome em snake-case)")
    sp_sub.add_argument("--label", help="Rótulo da sidebar")
    sp_sub.add_argument("--order", default="999", help="Ordem na sidebar")
    sp_sub.add_argument("--sidebar", action="store_true", help="Exibir na sidebar")
    sp_sub.add_argument("--force", action="store_true", help="Sobrescrever arquivo existente")
    sp_sub.set_defaults(func=cmd_new_subpage)

    # scaffold examples
    sp_ex = sub.add_parser("examples", help="Gerar página de exemplos de widgets/botões")
    sp_ex.add_argument("--force", action="store_true")
    sp_ex.set_defaults(func=cmd_scaffold_examples)

    # manifest update
    sp_mu = sub.add_parser("manifest-update", help="Reescrever app/assets/pages_manifest.json via auto-descoberta")
    sp_mu.set_defaults(func=cmd_manifest_update)

    # clean pages
    sp_clean = sub.add_parser("clean-pages", help="Remover páginas pré-programadas e criar Home vazia")
    sp_clean.add_argument("--rebuild-manifest", action="store_true", help="Recriar manifesto a partir da descoberta")
    sp_clean.set_defaults(func=cmd_clean_pages)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

