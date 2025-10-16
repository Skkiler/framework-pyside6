# app/app.py

from __future__ import annotations

import sys
from inspect import signature, Parameter
from PySide6.QtWidgets import QApplication

import app.settings as cfg
from ui.core.app_controller import AppController
from ui.core.settings import Settings

# Splash opcional
try:
    from ui.splash.splash import Splash  # type: ignore
except Exception:  # noqa: BLE001
    Splash = None  # type: ignore


def _make_splash() -> object | None:
    """Cria uma instância de Splash, tolerando diferentes assinaturas."""
    if Splash is None:
        return None

    candidates = {
        "assets_icons_dir": str(cfg.ASSETS_DIR / "icons"),
        "icons_dir":        str(cfg.ASSETS_DIR / "icons"),
        "assets_dir":       str(cfg.ASSETS_DIR),
        "assets_path":      str(cfg.ASSETS_DIR),
        "icons_path":       str(cfg.ASSETS_DIR / "icons"),
    }

    try:
        sig = signature(Splash)
        params = list(sig.parameters.values())

        accepted = {
            name: val
            for name, val in candidates.items()
            if any(p.name == name and p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
                   for p in params)
        }

        if accepted:
            try:
                return Splash(**accepted)
            except TypeError:
                pass

        non_self = [p for p in params if p.name != "self"]
        if len(non_self) == 1 and non_self[0].kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
            try:
                return Splash(str(cfg.ASSETS_DIR / "icons"))
            except Exception:
                try:
                    return Splash(str(cfg.ASSETS_DIR))
                except Exception:
                    pass

        return Splash()

    except Exception:
        # fallback simples
        for attempt in (
            lambda: Splash(assets_icons_dir=str(cfg.ASSETS_DIR / "icons")),
            lambda: Splash(str(cfg.ASSETS_DIR / "icons")),
            lambda: Splash(),
        ):
            try:
                return attempt()
            except Exception:
                continue
        return None


def _should_show_splash(settings: Settings) -> bool:
    """
    Verifica nas settings do usuário se o splash deve ser exibido.
    - chave: "splash"
    - True  → mostrar splash
    - False → pular splash
    """
    try:
        return bool(settings.read("splash", True))
    except Exception:
        return True  # fallback seguro


def main() -> None:
    app = QApplication(sys.argv)

    # Settings persistentes (cache)
    settings = Settings(cache_dir=cfg.CACHE_DIR, filename="_ui_exec_settings.json")

    controller = AppController(
        task_runner=None,
        assets_dir=str(cfg.ASSETS_DIR),
        base_qss_path=str(cfg.BASE_QSS),
        themes_dir=str(cfg.THEMES_DIR),
        default_theme=cfg.DEFAULT_THEME,
        first_page=cfg.FIRST_PAGE,
        manifest_filename=cfg.PAGES_MANIFEST_FILENAME,
        settings=settings,
        app_title=cfg.APP_TITLE,
    )

    # ---- Splash controlado pelas Settings ----
    show_splash = _should_show_splash(settings)
    if show_splash and Splash is not None:
        splash = _make_splash()
        if splash and hasattr(splash, "run"):
            splash.run(controller.show)
        else:
            controller.show()
    else:
        controller.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
