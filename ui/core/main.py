# ui/core/main.py

from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ui.core.app_controller import AppController
from ui.core.settings import Settings
from ui.splash.splash import Splash


# Runner “real” (ou de testes) – o AppController vai embrulhar com TaskRunnerAdapter
class DemoRunner:
    def run_task(self, name: str, payload: dict) -> dict:
        if name == "ping":
            return {"ok": True, "data": {"pong": True, "echo": payload}}
        if name == "proc_A":
            return {"ok": True, "data": {"message": "Proc A executada.", "recv": payload}}
        if name == "proc_B":
            import time
            heavy = bool(payload.get("heavy"))
            if heavy:
                time.sleep(1.0)
            return {"ok": True, "data": {"message": "Proc B finalizada.", "heavy": heavy}}
        return {"ok": False, "error": f"Tarefa desconhecida: {name}"}


def _resolve_assets_root() -> Path:
    # tenta <repo>/assets; se não, tenta <repo>/ui/assets
    root_dir = Path(__file__).resolve().parents[2]
    a = root_dir / "assets"
    if (a / "qss" / "base.qss").exists():
        return a
    b = root_dir / "ui" / "assets"
    if (b / "qss" / "base.qss").exists():
        return b
    return a  # fallback – qss_renderer tem defaults


def _build_controller(assets_dir: Path) -> AppController:
    controller = AppController(
        task_runner=DemoRunner(),
        assets_dir=str(assets_dir),
        auto_start=False,           # vamos startar manualmente
        default_theme="Dark",
        first_page="home",
    )
    return controller


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    assets_dir = _resolve_assets_root()
    icons_dir  = assets_dir / "icons"   # splash.png/gif aqui

    # === lê cache antes de decidir a splash ===
    cache_dir = assets_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        settings = Settings(cache_dir=cache_dir, filename="_ui_exec_settings.json")
    except TypeError:
        # fallback (versão antiga de Settings sem cache_dir)
        settings = Settings()

    show_splash = bool(settings.read("splash", True))  # default True = mostrar splash

    if not show_splash:
        # Pula a splash e vai direto pra janela principal
        controller = _build_controller(assets_dir)

        def _start_and_show():
            try:
                controller.start()   # aplica tema e registra páginas
            except Exception as e:
                print("[ERRO] ao iniciar AppController:", e)
            try:
                controller.show()    # mostra janela
            except Exception as e:
                print("[ERRO] ao dar show na janela:", e)

        QTimer.singleShot(0, _start_and_show)
        sys.exit(app.exec())

    # === fluxo com splash (comportamento antigo) ===
    splash = Splash(
        assets_icons_dir=str(icons_dir),
        title_text="Esses dias eu botei a Bruxa do 71 na chapa e foi deliciossissississississimo",
        hold_ms=1200,      # PNG: tempo na tela; GIF: respeita loops
        gif_loops=1,
        gif_speed=100,
    )
    splash.raise_()
    splash.activateWindow()

    controller_holder = {"controller": None}

    def _after():
        # Monta controller só quando o splash terminar
        controller = _build_controller(assets_dir)
        controller_holder["controller"] = controller

        # Inicia e força show() no próximo tick do loop
        def _start_and_show():
            try:
                controller.start()
            except Exception as e:
                print("[ERRO] ao iniciar AppController:", e)
            try:
                controller.show()
            except Exception as e:
                print("[ERRO] ao dar show na janela:", e)

            # encerrar splash por último
            splash.deleteLater()

        QTimer.singleShot(0, _start_and_show)

    splash.run(_after)
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
