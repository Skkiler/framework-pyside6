# ui/services/qss_renderer.py

from __future__ import annotations
from pathlib import Path
import re

# -----------------------------
# Defaults (cubra aqui os tokens que seu base.qss usa)
# -----------------------------
_DEFAULTS = {
    "bg_start": "#2f2f2f",
    "bg_end": "#3f3f3f",
    "bg": "#2f2f2f",
    "surface": "#383838",
    "text": "#e5e5e5",
    "muted": "#9aa1ac",

    "accent": "#347de9",
    "accent2": "#cc2727",     # alias opcional
    "accent-2": "#cc2727",    # alias opcional
    "danger": "#cc3333",

    "btn": "#3f7ad1",
    "btn_text": "#ffffff",
    "btn_hover": "#347de9",

    "input_bg": "#141111",
    "checkbox": "#e11717",
    "slider": "#e11717",

    "cond_selected": "#505050",
    "box_border": "#666666",

    "hover": "#347de9",
    "text_hover": "#ffffff",
    "window_bg": "#2f2f2f",
}

# Fallback mínimo caso o base.qss não exista
_FALLBACK_BASE = """
QWidget#RootWindow {
  background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {bg_start}, stop:1 {bg_end});
  color: {text};
  font: 12px 'Segoe UI', Arial;
}
QPushButton { background:{btn}; color:{btn_text}; border-radius:7px; padding:5px 12px; }
QPushButton:hover { background:{btn_hover}; }
QLineEdit { background:{input_bg}; color:{text}; border:1px solid {box_border}; border-radius:6px; padding:3px 8px; }
"""

# -----------------------------
# Regex de placeholders
# -----------------------------
_RX_DBL_BRACES = re.compile(r"\{\{([A-Za-z0-9_\-]+)\}\}")     # {{token}}
_RX_BRACES     = re.compile(r"\{([A-Za-z0-9_\-]+)\}")         # {token}
_RX_DOLLAR     = re.compile(r"\$\{([A-Za-z0-9_\-]+)\}")       # ${token}
# Limpezas finais
_RX_ANY_TOKEN        = re.compile(r"\{[A-Za-z0-9_\-]+\}")     # {foo}
_RX_LIT_HEX_BRACED   = re.compile(r"\{(#(?:[A-Fa-f0-9]{3}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8}))\}")

# -----------------------------
# Helpers de cor
# -----------------------------
def _parse_hex(s: str) -> tuple[int, int, int, int]:
    s = s.strip()
    if not s.startswith("#"):
        return (47, 47, 47, 255)
    s = s[1:]
    if len(s) == 3:  # #RGB
        r, g, b = (int(s[0]*2, 16), int(s[1]*2, 16), int(s[2]*2, 16))
        return (r, g, b, 255)
    if len(s) == 6:  # #RRGGBB
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
    if len(s) == 8:  # #AARRGGBB
        a = int(s[0:2], 16)
        return (int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16), a)
    return (47, 47, 47, 255)

def _clamp(x: float) -> int:
    return max(0, min(255, int(round(x))))

def _darken_hex(hex_color: str, factor: float) -> str:
    """factor < 1.0 escurece (ex.: 0.8 = 20% mais escuro)"""
    r, g, b, a = _parse_hex(hex_color)
    r = _clamp(r * factor); g = _clamp(g * factor); b = _clamp(b * factor)
    if a != 255:
        return f"#{a:02X}{r:02X}{g:02X}{b:02X}"
    return f"#{r:02X}{g:02X}{b:02X}"

# -----------------------------
# API
# -----------------------------
def load_base_qss(path: str | None) -> str:
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return _FALLBACK_BASE

def _normalize_vars(tokens: dict | None) -> dict:
    """Mescla tokens do tema com defaults + aliases, e cria derivados úteis."""
    vars_ = dict(_DEFAULTS)
    if isinstance(tokens, dict):
        vars_.update(tokens)

    # Aliases '-' <-> '_' (accent-2 vs accent_2)
    mirror = {}
    for k, v in list(vars_.items()):
        if "-" in k:
            mirror[k.replace("-", "_")] = v
        if "_" in k:
            mirror[k.replace("_", "-")] = v
    vars_.update(mirror)

    # Derivados: content_bg = bg_start ~20% mais escuro (para fundos sólidos)
    bg0 = vars_.get("bg_start", _DEFAULTS["bg_start"])
    vars_["content_bg"] = _darken_hex(bg0, 0.9)
    vars_["panel_bg"] = vars_["content_bg"]

    return vars_

def render_qss_from_base(base_qss: str, tokens: dict, *, debug_dump_path: str | None = None) -> str:
    """
    Substitui placeholders de forma robusta:
      - Suporta {{token}}, {token} e ${token};
      - Usa defaults quando faltar no tema;
      - Gera 'content_bg' automaticamente a partir de 'bg_start';
      - Remove {#RRGGBB} e quaisquer {token} remanescentes;
      - Opcionalmente grava o QSS final em debug_dump_path.
    """
    vars_ = _normalize_vars(tokens)

    out = base_qss

    # 1) {{token}} – tratar primeiro (remove ambas as chaves)
    def rep_dbl(m: re.Match) -> str:
        key = m.group(1)
        return str(vars_.get(key, _DEFAULTS.get(key, "transparent")))
    out = _RX_DBL_BRACES.sub(rep_dbl, out)

    # 2) ${token}
    def rep_dollar(m: re.Match) -> str:
        key = m.group(1)
        return str(vars_.get(key, _DEFAULTS.get(key, "transparent")))
    out = _RX_DOLLAR.sub(rep_dollar, out)

    # 3) {token}
    def rep_braces(m: re.Match) -> str:
        key = m.group(1)
        return str(vars_.get(key, _DEFAULTS.get(key, "transparent")))
    out = _RX_BRACES.sub(rep_braces, out)

    # 4) limpeza de literais {#RRGGBB} -> #RRGGBB
    out = _RX_LIT_HEX_BRACED.sub(r"\1", out)

    # 5) limpeza final – se ainda sobrou {qualquer_coisa}, troca por 'transparent'
    out = _RX_ANY_TOKEN.sub("transparent", out)

    # 6) dump opcional
    if debug_dump_path:
        try:
            Path(debug_dump_path).write_text(out, encoding="utf-8")
        except Exception:
            pass

    return out
