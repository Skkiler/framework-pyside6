from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Dict, Any

from PySide6.QtCore import Qt, QPoint, QTimer, QEvent
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QPushButton, QSizePolicy,
    QLabel, QMenu
)


MenuSpec = Dict[str, Any]


class Toolbar(QFrame):
    """Barra horizontal simples para o topo das páginas.

    - Use `add_button` para botões simples
    - Use `add_menu` para menus em cascata (hover/click)
    - Pode ser criada por página e registrada via AppShell.set_page_toolbar
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PageToolbar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(6)
        self._row = row
        row.addStretch(1)  # mantemos stretch; itens inseridos antes do stretch

    def add_widget(self, w: QWidget, *, at_left: bool = True) -> QWidget:
        # remove stretch e recoloca no fim
        count = self._row.count()
        if count > 0:
            item = self._row.takeAt(count - 1)
        else:
            item = None
        if at_left:
            self._row.insertWidget(0, w)
        else:
            self._row.addWidget(w)
        if item:
            self._row.addItem(item)
        return w

    def add_button(self, text: str, on_click: Optional[Callable[[], None]] = None) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setObjectName("ToolbarButton")
        btn.setCursor(Qt.PointingHandCursor)
        pol = btn.sizePolicy(); pol.setVerticalPolicy(QSizePolicy.Fixed); btn.setSizePolicy(pol)
        if on_click:
            btn.clicked.connect(on_click)
        self.add_widget(btn)
        return btn

    def add_menu(self, label: str, items: Sequence[MenuSpec], *, open_mode: str = "hover") -> QWidget:
        mb = ToolbarMenuButton(label, items, open_mode=open_mode, parent=self)
        self.add_widget(mb)
        return mb


class _MenuPanel(QMenu):
    """Popup baseado em QMenu com submenus (recursivo)."""

    def __init__(self, items: Sequence[MenuSpec], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ToolbarMenuPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self._subs: list[_MenuPanel] = []
        self._chain: set[_MenuPanel] = {self}

        for spec in items:
            if not spec:
                continue
            if spec.get("separator"):
                self.addSeparator(); continue
            text = str(spec.get("text", ""))
            sub = spec.get("submenu")
            trigger = spec.get("trigger")
            if sub:
                sm = _MenuPanel(sub, parent=self)
                sm.setTitle(text)
                # track chain
                sm.aboutToShow.connect(lambda sm=sm: self._chain.add(sm))
                sm.aboutToHide.connect(lambda sm=sm: self._chain.discard(sm))
                self._subs.append(sm)
                self.addMenu(sm)
            else:
                act = self.addAction(text)
                if callable(trigger):
                    act.triggered.connect(trigger)

    def all_open_menus(self) -> list['_MenuPanel']:
        return list(self._chain)


# (removido) _MenuItem — substituído por QMenu


class ToolbarMenuButton(QPushButton):
    """Botão de toolbar que abre menu em cascata.

    open_mode: 'hover' | 'click' | 'both'
    items: lista de dicts {text, trigger?, submenu?, hover?}
    """

    # Registro global do painel ativo (para fechar quando outro abre)
    _ACTIVE_OWNER: Optional["ToolbarMenuButton"] = None
    _ACTIVE_PANEL: Optional[_MenuPanel] = None

    def __init__(self, label: str, items: Sequence[MenuSpec], *, open_mode: str = "hover", parent=None):
        super().__init__(label, parent)
        self.setObjectName("ToolbarMenuButton")
        self.setCursor(Qt.PointingHandCursor)
        self._items = list(items)
        self._open_mode = (open_mode or "hover").lower()
        self._panel: Optional[_MenuPanel] = None
        self._opened_by_click: bool = False
        self._suppress_hover_until_leave: bool = False  # evita reabrir imediatamente após fechar por clique
        # Guarda proativa: verifica periodicamente se o cursor ainda está na
        # região permitida (botão + cadeia de painéis). Evita falsos fechamentos.
        self._hover_guard = QTimer(self)
        self._hover_guard.setInterval(80)
        self._hover_guard.timeout.connect(self._guard_tick)

        pol = self.sizePolicy(); pol.setVerticalPolicy(QSizePolicy.Fixed); self.setSizePolicy(pol)

        self.clicked.connect(self._on_click)
        self.setMouseTracking(True)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(200)
        self._hover_timer.timeout.connect(self._open_menu)

    def enterEvent(self, _):
        # Entrou no botão → abre por hover se não estiver visível
        if (self._open_mode in ("hover", "both")) and not (self._panel and self._panel.isVisible()):
            self._hover_timer.start()

    def leaveEvent(self, _):
        self._hover_timer.stop()

    def _on_click(self):
        # Clique apenas abre de forma temporária (sem persistência)
        if self._open_mode in ("click", "both"):
            self._open_menu(opened_by_click=False)

    def _open_menu(self, *, opened_by_click: bool = False):
        try:
            # fecha painel antigo
            if self._panel and self._panel.isVisible():
                self._panel.close()
            # fecha painel ativo de OUTRO botão
            if ToolbarMenuButton._ACTIVE_OWNER is not None and ToolbarMenuButton._ACTIVE_OWNER is not self:
                try:
                    ToolbarMenuButton._ACTIVE_OWNER._force_close(suppress_hover=False)
                except Exception:
                    pass
            self._panel = _MenuPanel(self._items, parent=self.window())
            self._panel.aboutToHide.connect(self._on_panel_hiding)
            # posição abaixo do botão
            gp = self.mapToGlobal(self.rect().bottomLeft())
            self._panel.popup(QPoint(gp.x(), gp.y()+2))
            # registra como ativo
            ToolbarMenuButton._ACTIVE_OWNER = self
            ToolbarMenuButton._ACTIVE_PANEL = self._panel
            # sempre temporário → guard ativo
            self._start_hover_guard()
        except Exception:
            pass

    # ---------- helpers ----------
    def _cursor_inside_panel_or_sub(self) -> bool:
        p = self._panel
        if p is None or not p.isVisible():
            return False
        pos = QCursor.pos()
        # verifica menu raiz + submenus abertos (coordenadas globais)
        try:
            rr = p.rect(); tl = p.mapToGlobal(rr.topLeft()); br = p.mapToGlobal(rr.bottomRight())
            from PySide6.QtCore import QRect
            if QRect(tl, br).adjusted(-2, -2, 2, 2).contains(pos):
                return True
        except Exception:
            pass
        if isinstance(p, _MenuPanel):
            for sm in p.all_open_menus():
                try:
                    if sm is p:
                        continue
                    rr2 = sm.rect(); tl2 = sm.mapToGlobal(rr2.topLeft()); br2 = sm.mapToGlobal(rr2.bottomRight())
                    from PySide6.QtCore import QRect
                    if QRect(tl2, br2).adjusted(-2,-2,2,2).contains(pos):
                        return True
                except Exception:
                    continue
        return False

    def _cursor_inside_self(self) -> bool:
        try:
            r = self.rect()
            tl = self.mapToGlobal(r.topLeft())
            br = self.mapToGlobal(r.bottomRight())
            from PySide6.QtCore import QRect
            return QRect(tl, br).adjusted(-2, -2, 2, 2).contains(QCursor.pos())
        except Exception:
            return False

    def _maybe_close_from_hover(self):
        # Só fecha se o cursor NÃO estiver no botão e também NÃO estiver
        # em nenhum painel/subpainel aberto
        if self._panel and self._panel.isVisible() and not (self._cursor_inside_self() or self._cursor_inside_panel_or_sub()):
            try:
                self._panel.hide()
            finally:
                self._opened_by_click = False
                if ToolbarMenuButton._ACTIVE_OWNER is self:
                    ToolbarMenuButton._ACTIVE_OWNER = None
                    ToolbarMenuButton._ACTIVE_PANEL = None
                self._stop_hover_guard()

    def _install_panel_events(self):
        if not self._panel:
            return
        return  # não usamos mais event filters por painel

    def _force_close(self, *, suppress_hover: bool):
        try:
            if self._panel and self._panel.isVisible():
                self._panel.hide()
        finally:
            if ToolbarMenuButton._ACTIVE_OWNER is self:
                ToolbarMenuButton._ACTIVE_OWNER = None
                ToolbarMenuButton._ACTIVE_PANEL = None
            self._stop_hover_guard()

    def eventFilter(self, obj, ev):
        return False

    # ---------- hover guard (proativo) ----------
    def _collect_panel_chain(self) -> list[_MenuPanel]:
        out: list[_MenuPanel] = []
        p = self._panel
        if isinstance(p, _MenuPanel) and p.isVisible():
            out.append(p)
            try:
                out.extend([sm for sm in p.all_open_menus() if sm is not p and sm.isVisible()])
            except Exception:
                pass
        return out

    def _allowed_hover_region_contains(self, gp) -> bool:
        # botão
        try:
            r = self.rect()
            tl = self.mapToGlobal(r.topLeft())
            br = self.mapToGlobal(r.bottomRight())
            from PySide6.QtCore import QRect
            if QRect(tl, br).adjusted(-2, -2, 2, 2).contains(gp):
                return True
        except Exception:
            pass
        # painéis
        for pan in self._collect_panel_chain():
            try:
                rr = pan.rect()
                tl2 = pan.mapToGlobal(rr.topLeft())
                br2 = pan.mapToGlobal(rr.bottomRight())
                from PySide6.QtCore import QRect
                if QRect(tl2, br2).adjusted(-2, -2, 2, 2).contains(gp):
                    return True
            except Exception:
                continue
        return False

    def _start_hover_guard(self):
        self._hover_guard.start()

    def _stop_hover_guard(self):
        self._hover_guard.stop()

    def _guard_tick(self):
        if not self._panel or not self._panel.isVisible():
            self._stop_hover_guard(); return
        gp = QCursor.pos()
        if not self._allowed_hover_region_contains(gp):
            self._maybe_close_from_hover()

    def _on_panel_hiding(self):
        if ToolbarMenuButton._ACTIVE_OWNER is self:
            ToolbarMenuButton._ACTIVE_OWNER = None
            ToolbarMenuButton._ACTIVE_PANEL = None
        self._stop_hover_guard()
