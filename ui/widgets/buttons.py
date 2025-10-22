# ui/widgets/buttons.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable, List, Tuple

from PySide6.QtCore import (
    QEasingCurve, QVariantAnimation, Qt, QSize, QRectF, Property, Signal,
    QTimer, QObject, QEvent, QPoint, QPropertyAnimation
)
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QBrush, QMouseEvent, QCursor, QPainterPath
from PySide6.QtWidgets import (
    QPushButton, QMessageBox, QGraphicsDropShadowEffect,
    QCheckBox, QComboBox, QLineEdit, QToolButton, QLabel,
    QWidget, QScrollArea, QFrame, QVBoxLayout, QSlider, QSizePolicy
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


class LinkLabel(QLabel):
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


class HoverButton(QPushButton):
    def __init__(
        self,
        text: str = "",
        parent=None,
        *,
        pad_x: Optional[int] = None,
        pad_y: Optional[int] = None,
        min_h: Optional[int] = None,
        fixed_w: Optional[int] = None,
        fixed_h: Optional[int] = None,
        size_preset: Optional[str] = None
    ):
        super().__init__(text, parent)

        self.setFlat(False)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setCursor(Qt.PointingHandCursor)

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

        # Presets de tamanho
        if size_preset:
            p = size_preset.strip().lower()
            if p == "char":
                self._pad_x, self._pad_y, self._min_h = 10, 6, 28
                if (self.text() or " ").strip().__len__() == 1:
                    self.setFixedWidth(max(self._min_h, 28))
            elif p == "sm":
                self._pad_x, self._pad_y, self._min_h = 12, 6, 30
            elif p == "md":
                self._pad_x, self._pad_y, self._min_h = 16, 7, 34
            elif p == "lg":
                self._pad_x, self._pad_y, self._min_h = 20, 8, 40
            elif p == "xl":
                self._pad_x, self._pad_y, self._min_h = 28, 12, 50
            self.setProperty("size", p)

        if fixed_w or fixed_h:
            if fixed_w: self.setFixedWidth(int(fixed_w))
            if fixed_h: self.setFixedHeight(int(fixed_h))
        else:
            sz = _autosize_for_text(self, self._pad_x, self._pad_y, self._min_h)
            self.setMinimumSize(sz)

        self.style().unpolish(self)
        self.style().polish(self)


    def setText(self, text: str) -> None:
        super().setText(text)
        # Se preset 'char' foi usado mas agora o texto tem >1 char, remova largura fixa.
        if self.property("size") == "char" and (text or "").strip().__len__() != 1:
            if self.maximumWidth() != 16777215:
                self.setMaximumWidth(16777215)
            if self.minimumWidth() != 0:
                self.setMinimumWidth(0)
        if self.maximumWidth() == 16777215 and self.maximumHeight() == 16777215:
            sz = _autosize_for_text(self, self._pad_x, self._pad_y, self._min_h)
            self.setMinimumSize(sz)
        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()

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

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self._shadow.setBlurRadius(16)
        self._shadow.setColor(QColor(0, 0, 0, 120))
        # empurra 1px para baixo (visual de clique)
        self.move(self.x(), self.y()+1)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self._shadow.setBlurRadius(8)
        self._shadow.setColor(QColor(0, 0, 0, 90))
        self.move(self.x(), self.y()-1)


class PrimaryButton(HoverButton):
    """Alias semântico para facilitar setProperty('variant','primary') no QSS, se quiser."""


class ToggleSwitch(QCheckBox):

    def __init__(self, parent=None, *, width: int = 34, height: int = 18, click_pad_right: int = 6):
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

        # interpola cores do trilho
        bg = self._mix(self._off_bg, self._on_bg, self._prog)

        # posição do botão (knob)
        knob_d = h - margin * 2.0
        x_off = margin
        x_on = w - margin - knob_d
        x = x_off + (x_on - x_off) * self._prog

        knob_col = self._mix(self._off_knob, self._on_knob, self._prog)

        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)

            # trilho (retângulo arredondado levemente “insetado” para borda nítida)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(bg))
            p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)

            # sombra leve do knob
            p.setBrush(QBrush(QColor(0, 0, 0, 60)))
            p.drawEllipse(QRectF(x + 0.8, margin + 0.8, knob_d, knob_d))

            # knob
            p.setBrush(QBrush(knob_col))
            p.setPen(QPen(QColor(0, 0, 0, 25), 1))
            p.drawEllipse(QRectF(x, margin, knob_d, knob_d))
        finally:
            p.end()


class InputList(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("shape", "top-rounded")

    def showPopup(self):
        super().showPopup()
        view = self.view()
        view.setObjectName("InputListPopup")


class CheckBoxControl(QCheckBox):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)


class TextInput(QLineEdit):
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(30)


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


class ExpandMoreButton(QWidget):

    class _Wrapper(QFrame):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._anim_h = 0
            self.setFrameShape(QFrame.NoFrame)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        def _get_h(self) -> int:
            return self._anim_h

        def _set_h(self, h: int):
            self._anim_h = max(0, int(h))
            self.setMinimumHeight(self._anim_h)
            self.setMaximumHeight(self._anim_h)
            self.updateGeometry()

        animHeight = Property(int, _get_h, _set_h)

    def __init__(self, target: QWidget, parent=None,
                 text_collapsed: str = "Ver mais detalhes",
                 text_expanded: str = "Ver menos detalhes",
                 duration_ms: int = 220):
        super().__init__(parent)
        self._target = target
        self._expanded = False
        self._text_collapsed = text_collapsed
        self._text_expanded = text_expanded
        self._duration = int(duration_ms)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Botão
        self.btn = PrimaryButton(self._text_collapsed, size_preset="sm")
        self.btn.setProperty("variant", "ghost")
        self.btn.setProperty("size", "sm")
        self.btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._apply_min_width()
        self._repolish(self.btn)
        self.btn.clicked.connect(self.toggle)
        root.addWidget(self.btn, 0, Qt.AlignLeft)

        # Wrapper + painel interno
        self._wrapper = ExpandMoreButton._Wrapper(self)

        try:
            p = target.parentWidget()
            if p and p.layout():
                p.layout().removeWidget(target)
        except Exception:
            pass

        self._panel = QFrame(self._wrapper)
        self._panel.setObjectName("ExpandMorePanel")
        self._panel.setAttribute(Qt.WA_StyledBackground, True)
        self._panel.setAutoFillBackground(False)

        pan_lay = QVBoxLayout(self._panel)
        pan_lay.setContentsMargins(10, 8, 10, 10)
        pan_lay.setSpacing(6)
        target.setParent(self._panel)
        target.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        pan_lay.addWidget(target)

        wrap_lay = QVBoxLayout(self._wrapper)
        wrap_lay.setContentsMargins(0, 0, 0, 0)
        wrap_lay.setSpacing(0)
        wrap_lay.addWidget(self._panel)

        # começa fechado
        self._wrapper.setMinimumHeight(0)
        self._wrapper.setMaximumHeight(0)
        self._wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._wrapper.show()  # mantemos no fluxo, mas colapsado
        root.addWidget(self._wrapper)

        # animação de altura
        self._h_anim = QPropertyAnimation(self._wrapper, b"animHeight", self)
        self._h_anim.setDuration(self._duration)
        self._h_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._h_anim.finished.connect(self._on_anim_finished)

        # contexto freezer de scroll
        self._scroll_ctx = None  # dict|None
        self._need_repolish = False

        # se quiser realmente esconder quando fechado, troque para True
        self._hide_when_collapsed = False

    # ---------- util ----------
    @staticmethod
    def _repolish(w: QWidget):
        s = w.style()
        s.unpolish(w)
        s.polish(w)

    def _apply_min_width(self):
        fm = QFontMetrics(self.btn.font())
        w = max(
            fm.horizontalAdvance(self._text_collapsed),
            fm.horizontalAdvance(self._text_expanded),
        )
        self.btn.setMinimumWidth(w + 28)

    def _find_scroller(self) -> Optional[QScrollArea]:
        w = self.parentWidget()
        while w is not None:
            if isinstance(w, QScrollArea):
                return w
            w = w.parentWidget()
        return None

    # ---------- freezer ----------
    def _freeze_scroll_start(self):
        sa = self._find_scroller()
        if not sa:
            self._scroll_ctx = None
            return
        vbar = sa.verticalScrollBar()
        if not vbar:
            self._scroll_ctx = None
            return

        old_max = vbar.maximum()
        val = vbar.value()

        keep_top = val
        keep_bottom = max(0, old_max - val)
        rel = 0.0 if old_max <= 0 else min(1.0, max(0.0, val / float(old_max)))

        NEAR = 48
        if keep_top <= NEAR:
            anchor = "top"
            keep = keep_top
        elif keep_bottom <= NEAR:
            anchor = "bottom"
            keep = keep_bottom
        else:
            anchor = "relative"
            keep = rel

        def set_value_safely(target_value: int):
            bs = vbar.blockSignals(True)
            vbar.setValue(max(0, min(vbar.maximum(), target_value)))
            vbar.blockSignals(bs)

        def on_range_changed(_min, new_max):
            if anchor == "top":
                tgt = min(keep, new_max)
            elif anchor == "bottom":
                tgt = max(0, new_max - keep)
            else:  # relative
                tgt = int(round(new_max * keep))
            set_value_safely(tgt)

        vbar.rangeChanged.connect(on_range_changed)

        self._scroll_ctx = {
            "area": sa,
            "bar": vbar,
            "anchor": anchor,
            "keep": keep,
            "slot": on_range_changed,
            "setter": on_range_changed,  # p/ snaps manuais
        }

    def _freeze_scroll_release_after_layout(self):
        """Solta o freezer após estabilizar layout; aplica 'duplo snap'."""
        ctx = self._scroll_ctx
        if not ctx:
            return
        vbar = ctx["bar"]

        def snap_once():
            try:
                ctx["setter"](vbar.minimum(), vbar.maximum())
            except Exception:
                pass

        # Snap imediato (range já deve ter estabilizado)
        snap_once()

        # Snap extra no próximo loop para capturar repaints/QSS tardios
        def final_release():
            snap_once()
            try:
                vbar.rangeChanged.disconnect(ctx["slot"])
            except Exception:
                pass
            self._scroll_ctx = None

        QTimer.singleShot(0, final_release)

    # ---------- api ----------
    def isExpanded(self) -> bool:
        return self._expanded

    def setExpanded(self, expanded: bool):
        if self._expanded == expanded:
            return

        self._expanded = bool(expanded)
        self._need_repolish = True

        if self._expanded:
            # ABRIR
            self._wrapper.show()
            self._wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            self._panel.updateGeometry()
            self._wrapper.updateGeometry()
            end_h = max(1, self._panel.sizeHint().height())
            start_h = max(0, self._wrapper.height())

            self._freeze_scroll_start()

            self._h_anim.stop()
            self._h_anim.setStartValue(start_h)
            self._h_anim.setEndValue(end_h)
            self.btn.setText(self._text_expanded)
            self._h_anim.start()
        else:
            # FECHAR
            self._panel.clearFocus()
            for w in self._panel.findChildren(QWidget):
                w.clearFocus()

            start_h = max(0, self._wrapper.height())

            self._freeze_scroll_start()

            self._h_anim.stop()
            self._h_anim.setStartValue(start_h)
            self._h_anim.setEndValue(0)
            self.btn.setText(self._text_collapsed)
            self._h_anim.start()

    def toggle(self):
        self.setExpanded(not self._expanded)

    # ---------- slots ----------
    def _on_anim_finished(self):
        # Mantém freezer ativo enquanto ajustamos políticas/tamanhos
        if self._expanded:
            # Aberto: solta limites e permite crescer naturalmente
            self._wrapper.setMinimumHeight(0)
            self._wrapper.setMaximumHeight(16777215)
            self._wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        else:
            # Fechado: NÃO usa hide(); colapsa mantendo no fluxo
            self._wrapper.setMinimumHeight(0)
            self._wrapper.setMaximumHeight(0)
            self._wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if self._hide_when_collapsed:
                QTimer.singleShot(0, self._wrapper.hide)
            else:
                self._wrapper.show()

        if self._need_repolish:
            self._repolish(self)
            self._need_repolish = False

        # Libera o freezer somente após o layout consolidar + snap extra
        QTimer.singleShot(0, self._freeze_scroll_release_after_layout)




class Popover(QFrame):

    def __init__(self, title: str, description: str, shortcut: Optional[str] = None,
                 parent: QWidget | None = None):
        super().__init__(parent, Qt.ToolTip)
        self.setObjectName("Popover")
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.setFrameShape(QFrame.NoFrame)

        # Defaults (podem ser alterados por QSS com qproperty-*)
        self._bgColor     = QColor(30, 30, 30, 230)
        self._borderColor = QColor(255, 255, 255, 60)
        self._borderWidth = 1
        self._radius      = 10

        # Conteúdo
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        lbl_title = QLabel(title, self)
        f = lbl_title.font(); f.setBold(True); lbl_title.setFont(f)
        lbl_desc = QLabel(description, self); lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_title); lay.addWidget(lbl_desc)

        if shortcut:
            lbl_short = QLabel(shortcut, self)
            sf = lbl_short.font(); sf.setPointSize(max(7, sf.pointSize() - 1)); lbl_short.setFont(sf)
            lbl_short.setProperty("hint", "shortcut")
            lay.addWidget(lbl_short)

        # Fade
        self._fading_out = False
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(140)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.finished.connect(self._on_fade_finished)

    # ---------- animação ----------
    def _on_fade_finished(self):
        if self._fading_out:
            self.hide()
            self._fading_out = False

    def show_near(self, anchor: QWidget):
        self._fading_out = False
        gpos = anchor.mapToGlobal(anchor.rect().bottomLeft())
        self.move(gpos + QPoint(0, 6))
        self.setWindowOpacity(0.0)
        self.show()
        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def fade_out(self):
        if not self.isVisible() or self._fading_out:
            return
        self._fading_out = True
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    # ---------- QProperties (para QSS) ----------
    def getBgColor(self): return self._bgColor
    def setBgColor(self, c):
        if c: self._bgColor = QColor(c); self.update()
    bgColor = Property(QColor, getBgColor, setBgColor)

    def getBorderColor(self): return self._borderColor
    def setBorderColor(self, c):
        if c: self._borderColor = QColor(c); self.update()
    borderColor = Property(QColor, getBorderColor, setBorderColor)

    def getBorderWidth(self): return self._borderWidth
    def setBorderWidth(self, w):
        try: w = int(w)
        except Exception: return
        self._borderWidth = max(0, w); self.update()
    borderWidth = Property(int, getBorderWidth, setBorderWidth)

    def getRadius(self): return self._radius
    def setRadius(self, r):
        try: r = int(r)
        except Exception: return
        self._radius = max(0, r); self.update()
    radius = Property(int, getRadius, setRadius)

    # ---------- pintura ----------
    def paintEvent(self, e):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)

            bw = float(max(0, self._borderWidth))
            inset = bw * 0.5
            # half-pixel para a borda ficar nítida
            rect = self.rect().adjusted(inset + 0.5, inset + 0.5,
                                        -(inset + 0.5), -(inset + 0.5))

            path = QPainterPath()
            path.addRoundedRect(rect, float(self._radius), float(self._radius))

            # fundo
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(self._bgColor))
            p.drawPath(path)

            # borda
            if bw > 0:
                pen = QPen(self._borderColor, bw)
                pen.setCosmetic(True)          # espessura consistente
                pen.setJoinStyle(Qt.RoundJoin) # junções suaves
                pen.setCapStyle(Qt.RoundCap)   # extremidades suaves
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawPath(path)
        finally:
            p.end()

        super().paintEvent(e)


class _HoverBinder(QObject):

        def __init__(self, anchor: QWidget, pop: Popover):
            super().__init__(anchor)
            self._anchor = anchor
            self._pop = pop

            self._show_timer = QTimer(self)
            self._show_timer.setSingleShot(True)
            self._show_timer.setInterval(500)  # antes: 1000 (um pouco mais responsivo)
            self._show_timer.timeout.connect(lambda: self._pop.show_near(self._anchor))

            self._hide_timer = QTimer(self)
            self._hide_timer.setSingleShot(True)
            self._hide_timer.setInterval(220)  # antes: 140 (dava corridas ao sair do anchor)
            self._hide_timer.timeout.connect(self._pop.fade_out)

            anchor.installEventFilter(self)
            pop.installEventFilter(self)

        def _cursor_near_pop(self, margin: int = 8) -> bool:
            """Retângulo de tolerância ao redor do popover para permitir a transição âncora→popover."""
            if not self._pop.isVisible():
                return False
            gp = QCursor.pos()
            r = self._pop.frameGeometry().adjusted(-margin, -margin, margin, margin)
            return r.contains(gp)

        def eventFilter(self, obj, ev):
            et = ev.type()
            if obj is self._anchor:
                if et in (QEvent.Enter, QEvent.HoverEnter):
                    self._hide_timer.stop()
                    self._show_timer.start()
                elif et in (QEvent.Leave, QEvent.HoverLeave):
                    # Se o cursor está se movendo para o popover, não dispara hide ainda
                    if self._cursor_near_pop():
                        self._hide_timer.stop()
                    else:
                        self._show_timer.stop()
                        self._hide_timer.start()
            elif obj is self._pop:
                if et in (QEvent.Enter, QEvent.HoverEnter):
                    self._hide_timer.stop()
                elif et in (QEvent.Leave, QEvent.HoverLeave):
                    # só inicia hide se não voltar imediatamente à âncora
                    if not self._anchor.underMouse():
                        self._hide_timer.start()
            return False

# helpers PopOver

def _shrink_anchor_to_content(anchor: QWidget) -> None:

    pol = anchor.sizePolicy()
    # evita Expanding/MinimumExpanding; usa Maximum para "abraçar" o conteúdo
    pol.setHorizontalPolicy(QSizePolicy.Maximum)
    anchor.setSizePolicy(pol)

    if isinstance(anchor, QLabel):
        # evita quebra de linha e calcula a largura do texto
        anchor.setWordWrap(False)
        fm = QFontMetrics(anchor.font())
        text = anchor.text() or ""
        w = fm.horizontalAdvance(text) + 2  # folga mínima
        h = max(anchor.sizeHint().height(), fm.height())
        anchor.setMinimumSize(w, h)
        anchor.setMaximumWidth(w)
        # garante que eventos de hover/move cheguem
        anchor.setMouseTracking(True)

    elif hasattr(anchor, "sizeHint"):
        # para botões/toolbuttons
        sh = anchor.sizeHint()
        anchor.setMinimumSize(sh)
        anchor.setMaximumWidth(sh.width())
        anchor.setMouseTracking(True)

def attach_popover(widget: QWidget, title: str, description: str, shortcut: Optional[str] = None) -> Popover:
    pop = Popover(title, description, shortcut, widget.window())

    try:
        _shrink_anchor_to_content(widget)
    except Exception:
        pass

    widget.setProperty("hasPopover", True)
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.style().unpolish(widget); widget.style().polish(widget)
    _HoverBinder(widget, pop)
    return pop

class UiSlider(QSlider):

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._progress_mode = False
        self.setTracking(True)
        self.setSingleStep(1)

    def setMode(self, mode: str):
        mode = (mode or "").strip().lower()
        self.setProgressMode(mode == "progress")

    def isProgressMode(self) -> bool:
        return self._progress_mode

    def setProgressMode(self, on: bool):
        self._progress_mode = bool(on)
        self.setProperty("progressMode", self._progress_mode)
        if self._progress_mode:
            self.setFocusPolicy(Qt.NoFocus)
            self.setEnabled(True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # <- bloqueia mouse
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setFocusPolicy(Qt.StrongFocus)
            self.setEnabled(True)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, e):
        if self._progress_mode: e.ignore(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self, e):
        if self._progress_mode: e.ignore(); return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self, e):
        if self._progress_mode: e.ignore(); return
        super().mouseReleaseEvent(e)


class StyledScrollArea(QScrollArea):
    """ScrollArea com políticas padrão sane e ganchos para QSS."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setObjectName("StyledScrollArea")


# ============================================================
# Helpers (botões de tarefa) — com bloqueio opcional
# ============================================================
def command_button(
    text: str,
    command_name: str,
    task_runner,
    payload: Optional[Dict[str, Any]] = None,
    *,
    disable_while_running: bool = True,   # desabilita o botão enquanto a task roda
    lock_after_click: bool = False,       # bloqueia o botão definitivamente após sucesso
    size_preset: Optional[str] = None,
    **size
) -> PrimaryButton:
    btn = PrimaryButton(text, size_preset=size_preset, **size)
    payload = payload or {}

    if task_runner is None or not hasattr(task_runner, "run_task"):
        btn.setEnabled(False)
        btn.setToolTip("Sem task_runner associado a este botão.")
    else:
        def on_click():
            if disable_while_running:
                btn.setEnabled(False)
            try:
                res = task_runner.run_task(command_name, payload)
            except Exception as e:
                if disable_while_running and not lock_after_click:
                    btn.setEnabled(True)
                QMessageBox.warning(btn, "Falha", f"Erro ao executar tarefa: {e}")
                return

            if not res.get("ok", False):
                if disable_while_running and not lock_after_click:
                    btn.setEnabled(True)
                QMessageBox.warning(btn, "Falha", str(res.get("error", "Erro desconhecido")))
                return

            # sucesso
            if lock_after_click:
                btn.setEnabled(False)
            elif disable_while_running:
                btn.setEnabled(True)

        btn.clicked.connect(on_click)

    return btn


def confirm_command_button(
    text: str,
    confirm_msg: str,
    command_name: str,
    task_runner,
    payload: Optional[Dict[str, Any]] = None,
    *,
    disable_while_running: bool = True,
    lock_after_click: bool = False,
    size_preset: Optional[str] = None,
    **size
) -> PrimaryButton:
    btn = PrimaryButton(text, size_preset=size_preset, **size)
    payload = payload or {}

    if task_runner is None or not hasattr(task_runner, "run_task"):
        btn.setEnabled(False)
        btn.setToolTip("Sem task_runner associado a este botão.")
    else:
        def on_click():
            ans = QMessageBox.question(btn, "Confirmar", confirm_msg)
            if ans == QMessageBox.Yes:
                if disable_while_running:
                    btn.setEnabled(False)
                try:
                    res = task_runner.run_task(command_name, payload)
                except Exception as e:
                    if disable_while_running and not lock_after_click:
                        btn.setEnabled(True)
                    QMessageBox.warning(btn, "Falha", f"Erro ao executar tarefa: {e}")
                    return

                if not res.get("ok", False):
                    if disable_while_running and not lock_after_click:
                        btn.setEnabled(True)
                    QMessageBox.warning(btn, "Falha", str(res.get("error", "Erro")))
                    return

                if lock_after_click:
                    btn.setEnabled(False)
                elif disable_while_running:
                    btn.setEnabled(True)

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

    # novos centralizados
    ExpandMore = ExpandMoreButton
    Popover    = Popover
    Slider     = UiSlider
    ScrollArea = StyledScrollArea
