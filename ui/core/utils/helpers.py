# Consolidated helpers for UI, animation, shadow, resize, buttons, and theme
from PySide6.QtCore import QPropertyAnimation, QObject, QEasingCurve, QPoint, QRect, QSize
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QColor, QFontMetrics
from typing import Optional, Tuple, Any, Dict, Type

# Animation

def create_animation(target: QObject, property_name: bytes, start_value, end_value, duration: int = 200, easing: QEasingCurve = QEasingCurve.OutCubic) -> QPropertyAnimation:
    anim = QPropertyAnimation(target, property_name)
    anim.setStartValue(start_value)
    anim.setEndValue(end_value)
    anim.setDuration(duration)
    anim.setEasingCurve(easing)
    return anim

# Shadow

def apply_shadow(widget: QWidget, color: QColor = QColor(0,0,0,120), blur_radius: int = 16, x_offset: int = 0, y_offset: int = 2) -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setColor(color)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(x_offset, y_offset)
    widget.setGraphicsEffect(shadow)
    return shadow

# Resize

def get_resize_edges(pos: QPoint, widget: QWidget, margin: int = 9) -> Tuple[bool, bool, bool, bool]:
    rect = widget.rect()
    left = abs(pos.x() - rect.left()) <= margin
    top = abs(pos.y() - rect.top()) <= margin
    right = abs(pos.x() - rect.right()) <= margin
    bottom = abs(pos.y() - rect.bottom()) <= margin
    return left, top, right, bottom

# Button autosize

def autosize_button(button: QPushButton, pad_x: int = 16, pad_y: int = 7, min_h: int = 34) -> QSize:
    fm = QFontMetrics(button.font())
    tw = fm.horizontalAdvance(button.text() or "")
    ih = button.iconSize().height() if not button.icon().isNull() else 0
    iw = button.iconSize().width() if not button.icon().isNull() else 0
    gap = 6 if iw > 0 and (button.text() or "") else 0
    w = tw + iw + gap + pad_x * 2
    h = max(min_h, max(fm.height() + pad_y * 2, ih + pad_y * 2))
    return QSize(w, h)

# Theme helpers

def is_hex(value: Any) -> bool:
    return isinstance(value, str) and value.strip().startswith("#")

def lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red()   + (b.red()   - a.red())   * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue()  + (b.blue()  - a.blue())  * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )

def rgba_from_hex(hex_str: str, alpha: float) -> str:
    c = QColor(hex_str)
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({c.red()},{c.green()},{c.blue()},{a:.2f})"

def coerce_vars(theme_obj: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(theme_obj, dict):
        return {}
    return theme_obj.get("vars") if isinstance(theme_obj.get("vars"), dict) else theme_obj

def make_tokens(base_vars: Dict[str, Any]) -> Dict[str, Any]:
    tokens = dict(base_vars)
    surface_hex = tokens.get("surface")
    if isinstance(surface_hex, str) and surface_hex.startswith("#"):
        tokens["loading_overlay_bg"] = rgba_from_hex(surface_hex, 0.05)
    else:
        tokens["loading_overlay_bg"] = "rgba(255,255,255,0.12)"
    return tokens

def create_layout_widget(
    layout_type: Type[QVBoxLayout | QHBoxLayout],
    parent: Optional[QWidget] = None,
    margin: int = 0,
    spacing: int = 0,
    widgets: list[QWidget] = None
) -> QWidget:
    """
    Helper para criar um widget com layout padrão.
    """
    container = QWidget(parent)
    layout = layout_type(container)
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)
    if widgets:
        for w in widgets:
            layout.addWidget(w)
    return container
