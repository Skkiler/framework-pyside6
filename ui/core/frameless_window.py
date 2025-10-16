# ui/core/frameless_window.py

from __future__ import annotations
from typing import Optional, Callable, Iterable

from PySide6.QtCore import (
    Qt, QRect, QPoint, QEasingCurve, QPropertyAnimation, QEvent, QSize, QObject,
    QParallelAnimationGroup, QSequentialAnimationGroup, QTimer, QEventLoop,
)
from PySide6.QtGui import QMouseEvent, QKeySequence, QCursor, QShortcut, QGuiApplication
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGraphicsDropShadowEffect, QDialog, QSizePolicy,
)

# =============================================================================
#  TUNÁVEIS (centralizados)
# =============================================================================
class _Fx:
    RESIZE_MARGIN       = 9
    CORNER_MARGIN       = 14
    TOP_RESIZE_PRIORITY = True
    TITLEBAR_DRAG_GAP   = 12
    DRAG_RESTORE_THRESH = 4
    SNAP_THRESHOLD      = 24
    GEO_MS_DEFAULT      = 340
    FADE_MS_DEFAULT     = 200


# =============================================================================
#  Janela principal sem moldura
# =============================================================================
class FramelessWindow(QMainWindow):

    # --------------------------------------------------------------------- init
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Flags/atributos de janela
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)

        # Estado interno
        self._titlebars: list[QWidget] = []
        self._draggables: list[QWidget] = []

        self._resizing = False
        self._resize_pos = QPoint()
        self._resize_edges = (False, False, False, False)  # left, top, right, bottom

        self._dragging = False
        self._drag_pos = QPoint()
        self._drag_press_global = QPoint()

        self._normal_geometry: Optional[QRect] = None
        self._is_maximized = False
        self._was_minimized = self.isMinimized()

        self._geo_anim: Optional[QPropertyAnimation] = None
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._anim_refs: list[QObject] = []  # guarda refs para grupos/anim

        self._geo_ms = _Fx.GEO_MS_DEFAULT
        self._fade_ms = _Fx.FADE_MS_DEFAULT

        self._shadow_effect: Optional[QGraphicsDropShadowEffect] = None
        self._shadow_ready = False
        self._heavy_animating = False
        self._first_show_done = False

        # ---- FRAME + CONTENT --------------------------------------------------
        self._frame = QWidget(self)
        self._frame.setObjectName("FramelessFrame")
        self._frame.setAutoFillBackground(True)
        self._frame.setAttribute(Qt.WA_StyledBackground, True)
        self._frame.setAttribute(Qt.WA_Hover, True)
        self._frame.setMouseTracking(True)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(1, 1, 1, 1)
        self._frame_layout.setSpacing(0)

        self._content = QWidget(self._frame)
        self._content.setObjectName("FramelessContent")
        self._content.setAttribute(Qt.WA_StyledBackground, True)
        self._content.setAttribute(Qt.WA_Hover, True)
        self._content.setMouseTracking(True)
        self._content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._frame_layout.addWidget(self._content)

        super().setCentralWidget(self._frame)

        # Filtros (após estado estabelecido)
        self._frame.installEventFilter(self)
        self._content.installEventFilter(self)

        # Atalhos
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self.minimize_with_fade)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.toggle_max_restore)

    # ================================================================== Sombra
    def _ensure_shadow(self):
        if self._shadow_ready:
            return
        try:
            eff = QGraphicsDropShadowEffect(self._frame)
            eff.setBlurRadius(24)
            eff.setOffset(0, 6)
            eff.setColor(self.palette().color(self.backgroundRole()))
            self._frame.setGraphicsEffect(eff)
            self._shadow_effect = eff
        except Exception:
            self._shadow_effect = None
        self._shadow_ready = True

    def _set_shadow_enabled(self, enabled: bool):
        if not self._shadow_ready or self._shadow_effect is None:
            return
        self._shadow_effect.setEnabled(enabled)

    # ============================================================ lifecycle UI
    def showEvent(self, e):
        self._ensure_shadow()
        super().showEvent(e)
        # Animação de primeira abertura (uma única vez)
        if not self._first_show_done:
            self._first_show_done = True
            self.setWindowOpacity(0.0)
            if not self._is_maximized:
                QTimer.singleShot(0, lambda: self._animate_fade(0.0, 1.0, dur=max(220, self._fade_ms)))
                g = self.geometry()
                self._animate_geometry_bounce(g, dur=max(220, self._geo_ms - 80), overshoot=0.035)
            else:
                QTimer.singleShot(0, lambda: self._animate_fade(0.0, 1.0, dur=max(220, self._fade_ms)))

    def changeEvent(self, e):
        # Detecta transições de estado da janela (minimizado <-> normal)
        if e.type() == QEvent.WindowStateChange:
            was_min = self._was_minimized
            now_min = self.isMinimized()
            if was_min and not now_min:  # restaurou
                self.setWindowOpacity(0.0)
                QTimer.singleShot(0, lambda: self._animate_fade(0.0, 1.0, dur=max(200, self._fade_ms)))
                if not self._is_maximized:
                    g = self.geometry()
                    self._animate_geometry_bounce(g, dur=max(200, self._geo_ms - 100), overshoot=0.035)
            self._was_minimized = now_min
        super().changeEvent(e)

    # =================================================================== API
    def content(self) -> QWidget:
        return self._content

    def set_animation_speeds(self, geometry_ms: int | None = None, fade_ms: int | None = None):
        if geometry_ms is not None:
            self._geo_ms = max(80, int(geometry_ms))
        if fade_ms is not None:
            self._fade_ms = max(80, int(fade_ms))

    def setCentralWidget(self, w: QWidget) -> None:  # noqa: N802 (Qt API)
        """Insere o widget dado dentro do content() mantendo um layout limpo."""
        layout = self._content.layout()
        if layout is None:
            layout = QVBoxLayout(self._content)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        else:
            # limpa widgets antigos
            while layout.count():
                item = layout.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)
        layout.addWidget(w)
        self._watch_widget_tree(w)

    def connect_titlebar(self, titlebar_widget: QWidget):
        """Marca um widget como área de drag e conecta botões padrão."""
        self.register_draggable(titlebar_widget)
        if titlebar_widget not in self._titlebars:
            self._titlebars.append(titlebar_widget)

        # Conecta sinais (se existirem)
        if hasattr(titlebar_widget, "minimizeRequested"):
            titlebar_widget.minimizeRequested.connect(self.minimize_with_fade)
        if hasattr(titlebar_widget, "maximizeRestoreRequested"):
            titlebar_widget.maximizeRestoreRequested.connect(self.toggle_max_restore)
        if hasattr(titlebar_widget, "closeRequested"):
            titlebar_widget.closeRequested.connect(self.close_with_shrink_fade)

        # Estado inicial do ícone Max/Restore
        if hasattr(titlebar_widget, "setMaximized"):
            try:
                titlebar_widget.setMaximized(self._is_maximized)
            except Exception:
                pass

    def register_draggable(self, w: QWidget):
        """Qualquer widget registrado aqui passa a arrastar a janela."""
        if w not in self._draggables:
            self._draggables.append(w)
            self._watch_widget_tree(w)

    # -------------------------------------------------------------- watcher/hit
    def _watch_widget_tree(self, root: QWidget):
        """Instala filtros e habilita hover/mouseTracking recursivamente."""
        stack: list[QWidget] = [root]
        while stack:
            obj = stack.pop()
            obj.setAttribute(Qt.WA_Hover, True)
            obj.setMouseTracking(True)
            obj.installEventFilter(self)
            for child in obj.children():
                if isinstance(child, QWidget):
                    stack.append(child)

    def _edge_hit(self, pos: QPoint) -> bool:
        l, t, r, b = self._calc_edges(pos)
        return any((l, t, r, b))

    def _top_resize_hit(self, pos: QPoint) -> bool:
        if self._is_maximized:
            return False
        return pos.y() <= max(_Fx.RESIZE_MARGIN, _Fx.TITLEBAR_DRAG_GAP)

    def _calc_edges(self, pos: QPoint) -> tuple[bool, bool, bool, bool]:
        """Retorna (left, top, right, bottom) se pos está em regiões de resize."""
        if self._is_maximized:
            return (False, False, False, False)

        r = self.rect()
        left   = pos.x() <= _Fx.RESIZE_MARGIN
        right  = pos.x() >= r.width()  - _Fx.RESIZE_MARGIN
        top    = pos.y() <= _Fx.RESIZE_MARGIN
        bottom = pos.y() >= r.height() - _Fx.RESIZE_MARGIN

        near_left   = pos.x() <= _Fx.CORNER_MARGIN
        near_right  = pos.x() >= r.width()  - _Fx.CORNER_MARGIN
        near_top    = pos.y() <= _Fx.CORNER_MARGIN
        near_bottom = pos.y() >= r.height() - _Fx.CORNER_MARGIN

        # diagonais antes — melhora UX
        if (near_left and near_top) or (near_right and near_bottom):
            return (near_left, near_top, near_right, near_bottom)
        if (near_right and near_top) or (near_left and near_bottom):
            return (near_left, near_top, near_right, near_bottom)

        return left, top, right, bottom

    def _update_cursor(self, pos: QPoint):
        if self._heavy_animating or self._is_maximized:
            return
        left, top, right, bottom = self._calc_edges(pos)
        if (left and top) or (right and bottom):
            self.setCursor(Qt.SizeFDiagCursor)
        elif (right and top) or (left and bottom):
            self.setCursor(Qt.SizeBDiagCursor)
        elif left or right:
            self.setCursor(Qt.SizeHorCursor)
        elif top or bottom:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()

    def _start_resize_from_edges(self, win_pos: QPoint):
        edges = self._calc_edges(win_pos)
        if not any(edges):
            if _Fx.TOP_RESIZE_PRIORITY and self._top_resize_hit(win_pos):
                edges = (False, True, False, False)
            else:
                return
        self._resizing = True
        self._resize_edges = edges
        self._resize_pos = self.mapToGlobal(win_pos)

    # ----------------------------------------------------------------- filters
    def eventFilter(self, obj: QObject, ev):
        # novos filhos => manter hover/resize funcionando
        if ev.type() == QEvent.ChildAdded:
            child = ev.child()
            if isinstance(child, QWidget):
                self._watch_widget_tree(child)

        # --- Draggables (TitleBar etc.)
        if obj in self._draggables:
            if ev.type() == QEvent.MouseButtonPress:
                me: QMouseEvent = ev  # type: ignore
                if me.button() == Qt.LeftButton:
                    win_pos = self.mapFromGlobal(me.globalPosition().toPoint())
                    if self._top_resize_hit(win_pos) and not self._is_maximized:
                        self._start_resize_from_edges(win_pos); return True
                    self._dragging = True
                    self._drag_press_global = me.globalPosition().toPoint()
                    if not self._is_maximized:
                        self._drag_pos = self._drag_press_global - self.frameGeometry().topLeft()
                    obj.setCursor(Qt.SizeAllCursor)
                    return True

            elif ev.type() == QEvent.MouseMove:
                me: QMouseEvent = ev  # type: ignore
                if self._resizing:
                    delta = me.globalPosition().toPoint() - self._resize_pos
                    self._perform_resize(delta)
                    self._resize_pos = me.globalPosition().toPoint()
                    return True

                if self._dragging:
                    gpos = me.globalPosition().toPoint()
                    if self._is_maximized and (gpos - self._drag_press_global).manhattanLength() > _Fx.DRAG_RESTORE_THRESH:
                        self._restore_from_max_at_cursor(gpos); return True
                    if not self._is_maximized:
                        self.move(gpos - self._drag_pos); return True

            elif ev.type() == QEvent.MouseButtonRelease:
                if self._dragging:
                    self._handle_snap_under_cursor()
                self._dragging = False
                obj.unsetCursor()
                return False

            elif ev.type() == QEvent.MouseButtonDblClick:
                self.toggle_max_restore(); return True

            elif ev.type() in (QEvent.Leave, QEvent.HoverLeave):
                self.unsetCursor()

            elif ev.type() in (QEvent.HoverMove,):
                hpos = self.mapFromGlobal(QCursor.pos())
                self._update_cursor(hpos)

        # --- Resize / cursor update (frame/conteúdo/draggables)
        if obj in (self._frame, self._content) or obj in self._draggables:
            if ev.type() in (QEvent.MouseMove, QEvent.HoverMove):
                if self._heavy_animating:
                    return False
                gpos = QCursor.pos() if ev.type() == QEvent.HoverMove else ev.globalPosition().toPoint()  # type: ignore
                if self._resizing:
                    delta = gpos - self._resize_pos
                    self._perform_resize(delta)
                    self._resize_pos = gpos
                    return True
                else:
                    win_pos = self.mapFromGlobal(gpos)
                    self._update_cursor(win_pos)
                    return False

            elif ev.type() == QEvent.MouseButtonPress:
                me: QMouseEvent = ev  # type: ignore
                if me.button() == Qt.LeftButton and not self._is_maximized:
                    win_pos = self.mapFromGlobal(me.globalPosition().toPoint())
                    if self._edge_hit(win_pos):
                        self._start_resize_from_edges(win_pos); return True

            elif ev.type() == QEvent.MouseButtonRelease:
                if self._resizing:
                    self._resizing = False; return True

            elif ev.type() in (QEvent.Leave, QEvent.HoverLeave):
                self.unsetCursor()

        return super().eventFilter(obj, ev)

    # -------------------------------------------------------------- mouse fallbacks
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self._is_maximized:
            edges = self._calc_edges(e.position().toPoint())
            if any(edges):
                self._resizing = True
                self._resize_edges = edges
                self._resize_pos = e.globalPosition().toPoint()
                e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            delta = e.globalPosition().toPoint() - self._resize_pos
            self._perform_resize(delta)
            self._resize_pos = e.globalPosition().toPoint()
            e.accept(); return
        else:
            self._update_cursor(e.position().toPoint())
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._resizing = False
        super().mouseReleaseEvent(e)

    # -------------------------------------------------------------- resize impl
    def _perform_resize(self, delta: QPoint):
        geo: QRect = self.geometry()
        left, top, right, bottom = self._resize_edges
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

        if left:
            x += delta.x(); w -= delta.x()
        if right:
            w += delta.x()
        if top:
            y += delta.y(); h -= delta.y()
        if bottom:
            h += delta.y()

        minw = max(self.minimumWidth(), 400)
        minh = max(self.minimumHeight(), 300)
        w = max(w, minw)
        h = max(h, minh)

        if w == minw and left:
            x = geo.right() - minw + 1
        if h == minh and top:
            y = geo.bottom() - minh + 1

        self.setGeometry(QRect(x, y, w, h))

    # ================================================================ animações
    def _keep_anim(self, anim: QObject):
        self._anim_refs.append(anim)

        def _cleanup():
            try:
                self._anim_refs.remove(anim)
            except ValueError:
                pass
        try:
            anim.finished.connect(_cleanup)  # type: ignore
        except Exception:
            pass
        return anim

    def _available_rect(self) -> QRect:
        # robusto mesmo sem windowHandle inicial
        try:
            screen = self.windowHandle().screen() if self.windowHandle() else None
            if screen is None:
                screen = self.screen()
            return screen.availableGeometry()
        except Exception:
            # fallback seguro
            return QRect(0, 0, 1280, 720)

    def _begin_heavy_anim(self):
        self._heavy_animating = True
        self._set_shadow_enabled(False)

    def _end_heavy_anim(self):
        self._set_shadow_enabled(True)
        self._heavy_animating = False

    def _mk_geo_anim(self, start: QRect, end: QRect, dur: int, easing=QEasingCurve.OutCubic):
        a = QPropertyAnimation(self, b"geometry")
        a.setDuration(dur)
        a.setStartValue(start)
        a.setEndValue(end)
        a.setEasingCurve(easing)
        return a

    def _animate_geometry(self, target: QRect, dur: int | None = None, easing=QEasingCurve.OutCubic):
        dur = self._geo_ms if dur is None else dur
        if self._geo_anim and self._geo_anim.state() == QPropertyAnimation.Running:
            self._geo_anim.stop()
        self._begin_heavy_anim()
        self._geo_anim = self._mk_geo_anim(self.geometry(), target, dur, easing)
        self._geo_anim.finished.connect(self._end_heavy_anim)
        self._keep_anim(self._geo_anim)
        self._geo_anim.start()

    def _animate_geometry_bounce(
        self,
        target: QRect,
        dur: int | None = None,
        overshoot: float = 0.06,
        curve_out=QEasingCurve.OutQuint,
        curve_back=QEasingCurve.OutBack,
    ):
        dur = self._geo_ms if dur is None else dur
        start = self.geometry()

        dx = int((target.x() - start.x()) * (1.0 + overshoot))
        dy = int((target.y() - start.y()) * (1.0 + overshoot))
        dw = int((target.width()  - start.width())  * (1.0 + overshoot))
        dh = int((target.height() - start.height()) * (1.0 + overshoot))
        overshoot_rect = QRect(start.x() + dx, start.y() + dy,
                               max(1, start.width() + dw), max(1, start.height() + dh))

        a1 = self._mk_geo_anim(start, overshoot_rect, int(dur * 0.65), curve_out)
        a2 = self._mk_geo_anim(overshoot_rect, target, int(dur * 0.35), curve_back)
        ec = QEasingCurve(curve_back); ec.setOvershoot(1.18)
        a2.setEasingCurve(ec)

        if self._geo_anim and self._geo_anim.state() == QPropertyAnimation.Running:
            self._geo_anim.stop()

        seq = QSequentialAnimationGroup(self)
        seq.addAnimation(a1); seq.addAnimation(a2)

        self._begin_heavy_anim()
        seq.finished.connect(self._end_heavy_anim)
        self._geo_anim = seq
        self._keep_anim(seq)
        seq.start()

    def _animate_fade(self, start: float, end: float, after: Optional[Callable] = None, dur: int | None = None,
                      curve=QEasingCurve.OutCubic):
        dur = self._fade_ms if dur is None else dur
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(dur)
        self._fade_anim.setStartValue(start)
        self._fade_anim.setEndValue(end)
        self._fade_anim.setEasingCurve(curve)
        if after:
            self._fade_anim.finished.connect(after)
        self._keep_anim(self._fade_anim)
        self._fade_anim.start()

    # ================================================================= ações
    def _stop_anims(self):
        if self._geo_anim and self._geo_anim.state() == QPropertyAnimation.Running:
            self._geo_anim.stop()
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()

    def minimize_with_fade(self):
        """Shrink + fade (suave) → só então minimizar (robusto)."""
        self._stop_anims()

        g = self.geometry()
        target_w = max(int(g.width() * 0.92), 200)
        target_h = max(int(g.height() * 0.92), 150)
        nx = g.center().x() - target_w // 2
        ny = g.center().y() - target_h // 2
        shrink_rect = QRect(nx, ny, target_w, target_h)

        geo = self._mk_geo_anim(g, shrink_rect, max(150, self._geo_ms - 160), QEasingCurve.OutBack)
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(max(160, self._fade_ms - 40))
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(geo)
        group.addAnimation(fade)

        def _do_min():
            try:
                self.showMinimized()
            finally:
                self.setWindowOpacity(1.0)
                self._end_heavy_anim()

        self._begin_heavy_anim()
        group.finished.connect(_do_min)
        self._keep_anim(group)
        group.start()

    def showNormal_with_fade(self):
        """Restaura com fade + micro-bounce para ‘respirar’."""
        self.showNormal(); self.raise_(); self.activateWindow()
        self.setWindowOpacity(0.0)
        self._animate_fade(0.0, 1.0, dur=max(180, self._fade_ms))
        g = self.geometry()
        self._animate_geometry_bounce(g, dur=max(200, self._geo_ms - 100), overshoot=0.035)

    def toggle_max_restore(self):
        """Alterna entre maximizado e restaurado com animação; avisa TitleBars do novo estado."""
        self._stop_anims()

        if not self._is_maximized:
            # Guardar geometria atual para restauração
            self._normal_geometry = self.geometry()
            target = self._available_rect()
            self._animate_geometry_bounce(
                target,
                overshoot=0.04,
                dur=self._geo_ms,
                curve_out=QEasingCurve.OutQuint,
                curve_back=QEasingCurve.OutBack
            )
            self._is_maximized = True
            self.unsetCursor()  # em modo max não mostramos cursores de resize
        else:
            # Restaura para a geometria anterior (ou fallback)
            target = self._normal_geometry if self._normal_geometry else QRect(
                self.x() + 60, self.y() + 40,
                max(900, self.width() - 120),
                max(560, self.height() - 80)
            )
            self._animate_geometry_bounce(
                target,
                overshoot=0.08,
                dur=self._geo_ms,
                curve_out=QEasingCurve.OutCubic,
                curve_back=QEasingCurve.OutBack
            )
            self._is_maximized = False

        # Notifica TitleBars conectados
        for tb in self._titlebars:
            if hasattr(tb, "setMaximized"):
                try:
                    tb.setMaximized(self._is_maximized)
                except Exception:
                    pass

    def shrink_to(self, size: QSize, center: bool = True, easing=QEasingCurve.OutBack, dur: int | None = None):
        """Encolhe suavemente até 'size' (opcionalmente centralizado)."""
        size = QSize(max(size.width(), 200), max(size.height(), 150))
        g = self.geometry()
        if center:
            nx = g.center().x() - size.width() // 2
            ny = g.center().y() - size.height() // 2
            target = QRect(nx, ny, size.width(), size.height())
        else:
            target = QRect(g.x(), g.y(), size.width(), size.height())
        self._animate_geometry_bounce(target, dur=dur or max(200, self._geo_ms - 80), overshoot=0.05)

    def close_with_shrink_fade(self):
        """Shrink com InBack + fade; fecha ao terminar (robusto)."""
        self._stop_anims()

        g = self.geometry()
        target_w = max(int(g.width() * 0.6), 280)
        target_h = max(int(g.height() * 0.6), 180)
        nx = g.center().x() - target_w // 2
        ny = g.center().y() - target_h // 2
        target = QRect(nx, ny, target_w, target_h)

        geo = self._mk_geo_anim(g, target, max(180, self._geo_ms - 120), QEasingCurve.InBack)
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(max(180, self._fade_ms))
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(geo)
        group.addAnimation(fade)

        def _do_close():
            try:
                self.close()
            finally:
                self.setWindowOpacity(1.0)
                self._end_heavy_anim()

        self._begin_heavy_anim()
        group.finished.connect(_do_close)
        self._keep_anim(group)
        group.start()

    # ================================================================= helpers
    def _restore_from_max_at_cursor(self, global_cursor: QPoint):
        """Restaura do maximizado e posiciona mantendo a proporção do cursor (sem animação)."""
        avail = self._available_rect()

        base_w = self._normal_geometry.width() if self._normal_geometry else int(avail.width() * 0.7)
        base_h = self._normal_geometry.height() if self._normal_geometry else int(avail.height() * 0.7)
        w = max(800, min(base_w, avail.width()))
        h = max(500, min(base_h, avail.height()))

        ratio = global_cursor.x() / max(1, avail.width())
        nx = global_cursor.x() - int(w * ratio)
        ny = global_cursor.y() - 20
        target = QRect(nx, ny, w, h)

        self._is_maximized = False
        self.setGeometry(target)  # sem animação
        self._drag_pos = global_cursor - target.topLeft()  # continua arrastando suave

    def _handle_snap_under_cursor(self):
        avail = self._available_rect()
        g = self.frameGeometry()
        cursor = QCursor.pos()

        near_left   = abs(cursor.x() - avail.left())   <= _Fx.SNAP_THRESHOLD
        near_right  = abs(cursor.x() - avail.right())  <= _Fx.SNAP_THRESHOLD
        near_top    = abs(cursor.y() - avail.top())    <= _Fx.SNAP_THRESHOLD

        if near_top and not (near_left or near_right):
            self._normal_geometry = g
            self._is_maximized = True
            self._animate_geometry(avail, easing=QEasingCurve.OutCubic)
            return

        if near_left and not near_right:
            self._is_maximized = False
            r = QRect(avail.left(), avail.top(), avail.width() // 2, avail.height())
            self._animate_geometry(r, easing=QEasingCurve.OutCubic)
            return

        if near_right and not near_left:
            self._is_maximized = False
            w = avail.width() // 2
            r = QRect(avail.right() - w + 1, avail.top(), w, avail.height())
            self._animate_geometry(r, easing=QEasingCurve.OutCubic)
            return

    # ================================================================= QoL
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._resizing:
            self._resizing = False
            e.accept(); return
        super().keyPressEvent(e)

    def resizeEvent(self, e):
        if self._is_maximized:
            self.unsetCursor()
        super().resizeEvent(e)


# =============================================================================
#  Diálogo frameless
# =============================================================================
class FramelessDialog(FramelessWindow):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setWindowModality(Qt.ApplicationModal)
        self._result_code = QDialog.Rejected
        self.setMinimumSize(360, 180)
        self._loop = None

        # Política de centralização: "window" (padrão), "screen" ou "parent"
        self._center_mode: str = "window"

    # ------------------- API pública extra -------------------
    def set_center_mode(self, mode: str):
        self._center_mode = mode if mode in ("window", "screen", "parent") else "window"

    # ------------------- Diálogo padrão (OK/Cancel) -------------------
    def accept(self):
        """Fecha o diálogo reportando QDialog.Accepted, com animação."""
        self._result_code = QDialog.Accepted
        try:
            self.close_with_shrink_fade()
        except Exception:
            self.close()

    def reject(self):
        """Fecha o diálogo reportando QDialog.Rejected, com animação."""
        self._result_code = QDialog.Rejected
        try:
            self.close_with_shrink_fade()
        except Exception:
            self.close()

    def exec(self) -> int:
        # Garante um tamanho razoável antes de centralizar
        if self.width() <= 1 or self.height() <= 1:
            sh = self.sizeHint()
            self.resize(sh if sh.isValid() else QSize(max(self.minimumWidth(), 360), max(self.minimumHeight(), 180)))
        self._center_over_parent()
        self.show()
        self._loop = QEventLoop(self)
        self._loop.exec()
        self._loop = None
        return self._result_code
    
    def closeEvent(self, e):
        try:
            if self._loop is not None and self._loop.isRunning():
                self._loop.quit()
        except Exception:
            pass
        super().closeEvent(e)

    # ------------------- Integração com TitleBar -------------------
    def connect_titlebar(self, titlebar_widget: QWidget):
        """Conecta a titlebar, mas mantém APENAS o botão de fechar visível."""
        super().connect_titlebar(titlebar_widget)
        for attr in ("btn_min", "btn_max", "_btn_settings"):
            if hasattr(titlebar_widget, attr):
                try:
                    getattr(titlebar_widget, attr).hide()
                except Exception:
                    pass

    # ------------------- Centralização -------------------
    def _center_over_parent(self):
        """Centraliza conforme a política (_center_mode)."""
        try:
            # 1) Tamanho útil
            if self.width() <= 1 or self.height() <= 1:
                sh = self.sizeHint()
                self.resize(sh if sh.isValid() else QSize(max(self.minimumWidth(), 360), max(self.minimumHeight(), 180)))

            # 2) Âncora (janela raiz, parent imediato, ou None)
            anchor = None
            if self._center_mode == "window":
                anchor = self.window()  # top-level (AppShell)
            elif self._center_mode == "parent":
                anchor = self.parentWidget()

            center_global = None
            if anchor and isinstance(anchor, QWidget) and anchor.isVisible():
                center_global = anchor.mapToGlobal(anchor.rect().center())

            # 3) Tela alvo
            screen = QGuiApplication.screenAt(center_global) if center_global else None
            if not screen:
                if anchor and anchor.windowHandle():
                    screen = anchor.windowHandle().screen()
                elif self.windowHandle():
                    screen = self.windowHandle().screen()
                else:
                    screen = QGuiApplication.primaryScreen()

            ag = screen.availableGeometry()

            # 4) Centro final (da tela ou do anchor)
            target_center = ag.center() if (self._center_mode == "screen" or center_global is None) else center_global
            x = target_center.x() - self.width() // 2
            y = target_center.y() - self.height() // 2

            # clamp dentro da área visível
            x = max(ag.left(),  min(x, ag.right()  - self.width()  + 1))
            y = max(ag.top(),   min(y, ag.bottom() - self.height() + 1))
            self.move(x, y)
        except Exception:
            pass

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._center_over_parent)

    def eventFilter(self, obj: QObject, ev):
        # Evita maximizar por duplo-clique em diálogos
        if obj in getattr(self, "_draggables", []) and ev.type() == QEvent.MouseButtonDblClick:
            return True
        return super().eventFilter(obj, ev)