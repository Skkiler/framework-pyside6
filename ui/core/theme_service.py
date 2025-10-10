# ui/core/theme_service.py

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimeLine
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from ..services.qss_renderer import load_base_qss, render_qss_from_base
from .settings import Settings
from .interface_ports import IThemeRepository


# ---------- Helpers ----------

def _is_hex(s: Any) -> bool:
    return isinstance(s, str) and s.strip().startswith("#")

def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red()   + (b.red()   - a.red())   * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue()  + (b.blue()  - a.blue())  * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )

def _rgba_from_hex(hex_str: str, alpha: float) -> str:
    c = QColor(hex_str)
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({c.red()},{c.green()},{c.blue()},{a:.2f})"


class ThemeService(QObject):
    themeApplied = Signal(str)

    def __init__(
        self,
        repo: IThemeRepository,
        root: QWidget,
        settings: Optional[Settings] = None,
        base_qss_path: Optional[str] = None,
        animate_ms_default: int = 400,
        *,
        cache_dir: Optional[str | Path] = None,   # <<< novo
    ):
        super().__init__(root)
        self._repo = repo
        self._root = root
        self._animate_ms_default = animate_ms_default
        self._timeline: Optional[QTimeLine] = None
        self._current_name: Optional[str] = None
        self._base_qss = load_base_qss(base_qss_path)

        # --- cache dir ---
        self._cache_dir = Path(cache_dir) if cache_dir else (Path.home() / ".ui_exec_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._dump_qss_path = self._cache_dir / "last_applied.qss"

        # Settings: se sua classe aceitar base_dir, usamos; caso contrário, cai no padrão
        if settings is not None:
            self._settings = settings
        else:
            try:
                self._settings = Settings(base_dir=str(self._cache_dir))
            except TypeError:
                # versão antiga sem base_dir
                self._settings = Settings()

    # ---------- API alto nível ----------
    def available(self) -> list[str]:
        return self._repo.list_themes()

    def current(self) -> Optional[str]:
        return self._current_name

    def load_selected_from_settings(self) -> Optional[str]:
        return self._settings.read("theme", None)

    def apply(
        self,
        theme_name: str,
        animate: bool = True,
        persist: bool = True,
        duration_ms: Optional[int] = None
    ) -> None:
        data = self._repo.load_theme(theme_name)
        if not isinstance(data, dict):
            return
        old = self._repo.load_theme(self._current_name) if self._current_name else None

        if animate and old:
            self._animate_apply(old, data, duration_ms or self._animate_ms_default)
        else:
            self._apply_now(data)

        self._current_name = theme_name
        if persist:
            self._settings.write("theme", theme_name)
        self.themeApplied.emit(theme_name)

    # ---------- Internals ----------
    def _apply_now(self, theme: Dict[str, Any]) -> None:
        app = QApplication.instance()
        if not app:
            return

        # 1) Palette mínima (opcional)
        pal = app.palette()
        palette_map = (theme.get("palette") or {}) if isinstance(theme.get("palette"), dict) else {}
        for role_name, hex_color in palette_map.items():
            if hasattr(QPalette, role_name) and _is_hex(hex_color):
                pal.setColor(getattr(QPalette, role_name), QColor(hex_color))
        app.setPalette(pal)

        # 2) QSS (base.qss + tokens “vars” + tokens derivados)
        tokens = theme.get("vars") or theme
        if not isinstance(tokens, dict):
            tokens = {}

        # Derivado: cor do painel do LoadingOverlay com ~20% de opacidade da cor 'slider'
        tokens = dict(tokens)  # não muta o original
        checkbox_hex = tokens.get("checkbox")
        if isinstance(checkbox_hex, str) and checkbox_hex.startswith("#"):
            tokens["loading_overlay_bg"] = _rgba_from_hex(checkbox_hex, 0.05)
        else:
            tokens["loading_overlay_bg"] = "rgba(255,255,255,0.12)"  # fallback sutil

        qss = render_qss_from_base(
            self._base_qss,
            tokens,
            debug_dump_path=str(self._dump_qss_path)  # <<< salva na pasta de cache
        )

        try:
            self._root.setStyleSheet(qss)
        except Exception:
            # último recurso para não travar se houver erro de QSS
            safe = "\n".join(
                line for line in qss.splitlines()
                if ("{" in line and "}" in line) or ":" in line
            )
            try:
                self._root.setStyleSheet(safe)
            except Exception:
                pass

    def _animate_apply(self, old: Dict[str, Any], new: Dict[str, Any], ms: int) -> None:
        if self._timeline:
            try:
                self._timeline.stop()
            except Exception:
                pass

        self._timeline = QTimeLine(ms, self)
        self._timeline.setFrameRange(0, 100)

        old_vars = (old.get("vars") or old) if isinstance(old, dict) else {}
        new_vars = (new.get("vars") or new) if isinstance(new, dict) else {}
        keys = {k for k in old_vars.keys() & new_vars.keys() if _is_hex(old_vars[k]) and _is_hex(new_vars[k])}

        def frame_changed(i: int):
            t = i / 100.0
            mix = dict(new)
            mix_vars = dict(new_vars)
            for k in keys:
                ca, cb = QColor(old_vars[k]), QColor(new_vars[k])
                mix_vars[k] = _lerp(ca, cb, t).name(
                    QColor.HexArgb if (ca.alpha() != 255 or cb.alpha() != 255) else QColor.HexRgb
                )
            mix["vars"] = mix_vars
            self._apply_now(mix)

        def finished():
            self._apply_now(new)

        self._timeline.frameChanged.connect(frame_changed)
        self._timeline.finished.connect(finished)
        self._timeline.start()
