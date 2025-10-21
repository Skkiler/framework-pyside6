# ui/widgets/buttons.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable

from PySide6.QtCore import QEasingCurve, QVariantAnimation, Qt, QSize, QRectF, Property, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QBrush, QMouseEvent, QCursor
from PySide6.QtWidgets import (
    QPushButton, QMessageBox, QGraphicsDropShadowEffect,
    QCheckBox, QComboBox, QLineEdit, QToolButton, QLabel
)

# ---------- autosize util ----------
def _autosize_for_text(widget: QPushButton, pad_x: int = 16, pad_y: int = 7, min_h: int = 34) -> QSize:
    fm = QFontMetrics(widget.font())
    tw = fm.horizontalAdvance(widget.text() or "")
    ih = widget.iconSize().height() if not widget.icon().isNull() else 0
    iw = widget.iconSize().width() if not widget.icon().isNull() else 0
    gap = 6 if iw > 0 and (widget.text() or "") else 0
    w = tw + iw + gap + pad_x * 2
    h = max(min_h, max(fm.height() + pad_y * 2, ih + pad_y * 2))
    return QSize(w, h)


# ============================================================
# LinkLabel — parece texto, mas é clicável; troca cor no hover via QSS
# ============================================================
class LinkLabel(QLabel):
    """
    Rótulo clicável, estilo “texto”. Não tem moldura, padding nem fundo.
    - Usa cursor de mão.
    - Emite `clicked` no mouse release com botão esquerdo.
    - Seta a propriedade dinâmica `hover` True/False para o QSS controlar cor.
    Exemplo de QSS:
        #BreadcrumbLink { color: palette(window-text); }
        #BreadcrumbLink[hover="true"] { color: @accent; }   // ou sua var de hover
        #BreadcrumbLink[current="true"] { color: palette(mid); }
    """
    clicked = Signal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setProperty("hover", False)

    def enterEvent(self, e):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
            e.accept()
            return
        super().mouseReleaseEvent(e)


# ============================================================
# HoverButton (base, com glow e autosize) / PrimaryButton
# ============================================================
class HoverButton(QPushButton):
    """
    Botão com feedback de hover sem mexer em geometry (não "deforma").
    Auto-size por padrão; opcionalmente aceite fixed_w/fixed_h.
    """
    def __init__(
        self,
        text: str = "",
        parent=None,
        *,
        pad_x: Optional[int] = None,
        pad_y: Optional[int] = None,
        min_h: Optional[int] = None,
        fixed_w: Optional[int] = None,
        fixed_h: Optional[int] = None
    ):
        super().__init__(text, parent)

        # Glow/sombra
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, 0)
        self._shadow.setBlurRadius(4)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self._shadow)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._apply_progress)

        self.setCursor(Qt.PointingHandCursor)

        # Defaults caso não leia do tema
        self._pad_x = 16 if pad_x is None else int(pad_x)
        self._pad_y = 7  if pad_y is None else int(pad_y)
        self._min_h = 34 if min_h is None else int(min_h)

        if fixed_w or fixed_h:
            if fixed_w: self.setFixedWidth(int(fixed_w))
            if fixed_h: self.setFixedHeight(int(fixed_h))
        else:
            sz = _autosize_for_text(self, self._pad_x, self._pad_y, self._min_h)
            self.setMinimumSize(sz)

    def setText(self, text: str) -> None:
        super().setText(text)
        # re-calcula se não estiver com tamanho fixo
        if self.maximumWidth() == 16777215 and self.maximumHeight() == 16777215:
            sz = _autosize_for_text(self, self._pad_x, self._pad_y, self._min_h)
            self.setMinimumSize(sz)

    def _apply_progress(self, t: float):
        blur = 4 + (14 - 4) * float(t)
        alpha = int(90 * float(t))
        self._shadow.setBlurRadius(blur)
        self._shadow.setColor(QColor(0, 0, 0, alpha))

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setDirection(QVariantAnimation.Forward)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setDirection(QVariantAnimation.Backward)
        self._anim.start()
        super().leaveEvent(e)


class PrimaryButton(HoverButton):
    """Alias semântico para facilitar setProperty('variant','primary') no QSS, se quiser."""


# ============================================================
# ToggleSwitch – animado (pintado à mão)
# ============================================================
class ToggleSwitch(QCheckBox):
    """
    ToggleSwitch animado e tematizável via QSS.
    """
    def __init__(self, parent=None, *, width: int = 34, height: int = 18):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setTristate(False)
        self.setFocusPolicy(Qt.StrongFocus)

        # dimensões
        self._w = max(28, int(width))
        self._h = max(14, int(height))

        # estado animado (0.0 -> 1.0)
        self._prog = 1.0 if self.isChecked() else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._start_anim)

        # Cores padrão (caso não definidas via qproperty)
        pal = self.palette()
        self._off_bg   = pal.dark().color()
        self._off_knob = pal.window().color()
        self._on_bg    = pal.highlight().color()
        self._on_knob  = QColor(255, 255, 255)

    # ---------- QPropertys para QSS ----------
    def getOffBg(self): return self._off_bg
    def setOffBg(self, c):
        if c: self._off_bg = QColor(c)
        self.update()
    offBg = Property(QColor, getOffBg, setOffBg)

    def getOffKnob(self): return self._off_knob
    def setOffKnob(self, c):
        if c: self._off_knob = QColor(c)
        self.update()
    offKnob = Property(QColor, getOffKnob, setOffKnob)

    def getOnBg(self): return self._on_bg
    def setOnBg(self, c):
        if c: self._on_bg = QColor(c)
        self.update()
    onBg = Property(QColor, getOnBg, setOnBg)

    def getOnKnob(self): return self._on_knob
    def setOnKnob(self, c):
        if c: self._on_knob = QColor(c)
        self.update()
    onKnob = Property(QColor, getOnKnob, setOnKnob)

    # ---------- sizing ----------
    def sizeHint(self) -> QSize:
        return QSize(self._w, self._h)

    # ---------- anim ----------
    def _start_anim(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._prog)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _on_anim(self, v):
        self._prog = float(v)
        self.update()

    # ---------- helper ----------
    @staticmethod
    def _mix(a: QColor, b: QColor, t: float) -> QColor:
        return QColor(
            int(a.red()   + (b.red()   - a.red())   * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue()  + (b.blue()  - a.blue())  * t),
            int(a.alpha() + (b.alpha() - a.alpha()) * t),
        )

    # ---------- pintura ----------
    def paintEvent(self, _):
        w, h = self._w, self._h
        self.resize(w, h)
        radius = h / 2.0
        margin = 1.5

        # interpola cores trilho
        bg = self._mix(self._off_bg, self._on_bg, self._prog)

        # posição do botão
        knob_d = h - margin * 2.0
        x_off = margin
        x_on = w - margin - knob_d
        x = x_off + (x_on - x_off) * self._prog

        knob_col = self._mix(self._off_knob, self._on_knob, self._prog)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # trilho
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # sombra leve do knob
        p.setBrush(QBrush(QColor(0, 0, 0, 60)))
        p.drawEllipse(QRectF(x + 0.8, margin + 0.8, knob_d, knob_d))

        # knob
        p.setBrush(QBrush(knob_col))
        p.setPen(QPen(QColor(0, 0, 0, 25), 1))
        p.drawEllipse(QRectF(x, margin, knob_d, knob_d))

        p.end()


# ============================================================
# InputList
# ============================================================
class InputList(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("shape", "top-rounded")

    def showPopup(self):
        super().showPopup()
        view = self.view()
        view.setObjectName("InputListPopup")


# ============================================================
# CheckBoxControl / TextInput
# ============================================================
class CheckBoxControl(QCheckBox):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)


class TextInput(QLineEdit):
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(30)

# ============================================================
# IconButton
# ============================================================
class IconButton(QToolButton):

    def __init__(self, text: str = "", parent=None, *, tooltip: str = ""):
        super().__init__(parent)
        self.setText(text)
        if tooltip:
            self.setToolTip(tooltip)
        self.setAutoRaise(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(28, 28)
        self.setProperty("variant", "ghost")

# ============================================================
# Helpers (como você já usava)
# ============================================================
def command_button(
    text: str,
    command_name: str,
    task_runner,
    payload: Optional[Dict[str, Any]] = None,
    **size
) -> PrimaryButton:
    btn = PrimaryButton(text, **size)
    payload = payload or {}

    if task_runner is None or not hasattr(task_runner, "run_task"):
        btn.setEnabled(False)
        btn.setToolTip("Sem task_runner associado a este botão.")
    else:
        def on_click():
            try:
                res = task_runner.run_task(command_name, payload)
            except Exception as e:
                QMessageBox.warning(btn, "Falha", f"Erro ao executar tarefa: {e}")
                return
            if not res.get("ok", False):
                QMessageBox.warning(btn, "Falha", str(res.get("error", "Erro desconhecido")))
        btn.clicked.connect(on_click)

    return btn

def confirm_command_button(
    text: str,
    confirm_msg: str,
    command_name: str,
    task_runner,
    payload: Optional[Dict[str, Any]] = None,
    **size
) -> PrimaryButton:
    btn = PrimaryButton(text, **size)
    payload = payload or {}

    if task_runner is None or not hasattr(task_runner, "run_task"):
        btn.setEnabled(False)
        btn.setToolTip("Sem task_runner associado a este botão.")
    else:
        def on_click():
            ans = QMessageBox.question(btn, "Confirmar", confirm_msg)
            if ans == QMessageBox.Yes:
                try:
                    res = task_runner.run_task(command_name, payload)
                except Exception as e:
                    QMessageBox.warning(btn, "Falha", f"Erro ao executar tarefa: {e}")
                    return
                if not res.get("ok", False):
                    QMessageBox.warning(btn, "Falha", str(res.get("error", "Erro")))
        btn.clicked.connect(on_click)

    return btn


def route_button(text: str, goto: Callable[[], None], **size) -> PrimaryButton:
    btn = PrimaryButton(text, **size)
    btn.clicked.connect(goto)
    return btn


# ============================================================
# Consolidador para import fácil
# ============================================================
class Controls:
    Toggle     = ToggleSwitch
    InputList  = InputList
    Button     = PrimaryButton
    CheckBox   = CheckBoxControl
    TextInput  = TextInput
    IconButton = IconButton
    LinkLabel  = LinkLabel
