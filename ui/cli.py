from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
from datetime import datetime

# --- utils de nome ---
def to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name.strip())
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return re.sub(r"[\W]+", "_", s2).lower().strip("_")

def to_camel(name: str) -> str:
    parts = re.split(r"[\W_]+", name.strip())
    return "".join(p.capitalize() for p in parts if p)

# --- template da página ---
PAGE_TEMPLATE = """\
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

PAGE = {{
    "route": "{route}",
    "label": "{label}",
    "sidebar": {sidebar},
    "order": {order},
}}

class {class_name}(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Página: {label}"))

    # --- hooks de ciclo de vida (opcionais) ---
    def on_enter(self, params: dict | None = None):
        # chamado sempre que a rota é ativada
        # params pode conter dados de navegação: filtros, ids etc.
        pass

    def on_leave(self):
        # chamado antes de sair da rota (cancelar timers, salvar estado etc.)
        pass

    @staticmethod
    def build(task_runner=None, theme_service=None):
        return {class_name}(task_runner=task_runner, theme_service=theme_service)

# ====== FACTORY ======
def build(task_runner=None, theme_service=None):
    return {class_name}.build(task_runner=task_runner, theme_service=theme_service)
"""

def cmd_new_page(args):
    base = Path(__file__).resolve().parents[0]   # ui/
    pages_dir = base / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    class_name = to_camel(args.name) + "Page"
    route = args.route or to_snake(args.name)
    label = args.label or args.name
    order = int(args.order)
    sidebar = "True" if args.sidebar else "False"

    filename = f"{route}_page.py"
    target = pages_dir / filename

    if target.exists() and not args.force:
        print(f"[ERRO] Arquivo já existe: {target}\nUse --force para sobrescrever.")
        sys.exit(2)

    content = PAGE_TEMPLATE.format(
        route=route, label=label, order=order, sidebar=sidebar, class_name=class_name
    )

    header = f"# Auto-gerado por ui.cli em {datetime.now().isoformat(timespec='seconds')}\n"
    target.write_text(header + "\n" + content, encoding="utf-8")

    print(f"[OK] Página criada: {target}")
    print(f" - Rota: {route}")
    print(f" - Classe: {class_name}")
    print("Dica: reinicie o app; a página será descoberta automaticamente via registry.")

def build_parser():
    p = argparse.ArgumentParser(prog="ui-cli", description="Ferramentas de DX do framework UI.")
    sub = p.add_subparsers(dest="command", required=True)

    # new page
    sp = sub.add_parser("new", help="Gerar artefatos (páginas, etc.)")
    ssub = sp.add_subparsers(dest="artifact", required=True)

    sp_page = ssub.add_parser("page", help="Cria uma nova página em ui/pages")
    sp_page.add_argument("name", help="Nome lógico da página (ex.: Relatorios, ConfigAvancada)")
    sp_page.add_argument("--route", help="Rota (default: nome em snake case)")
    sp_page.add_argument("--label", help="Rótulo da sidebar (default: name)")
    sp_page.add_argument("--order", default="999", help="Ordem na sidebar (default: 999)")
    sp_page.add_argument("--sidebar", action="store_true", help="Exibir na sidebar (default: False)")
    sp_page.add_argument("--force", action="store_true", help="Sobrescrever arquivo existente")

    sp_page.set_defaults(func=cmd_new_page)

    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
