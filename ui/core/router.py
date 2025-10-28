# ui/core/router.py

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QStackedWidget, QWidget, QScrollArea, QFrame, QVBoxLayout


class Router(QStackedWidget):
    """
    Router v2: suporte a caminhos hierárquicos (ex.: 'db/conexoes'),
    histórico (back/forward), persistência externa via sinais e
    hook de ciclo de vida `on_route(params)`.
    """

    # Sinal para quem quiser reagir a navegação (breadcrumb, persistência, log, etc.)
    # Emite: (path:str, params:dict)
    routeChanged = Signal(str, dict)

    def __init__(self, parent=None, *, history_limit: int = 100):
        super().__init__(parent)
        self.setObjectName("AppContentArea")

        # Mapa de rotas -> QWidget
        self._pages: Dict[str, QWidget] = {}

        # Rota atual (path hierárquico)
        self._current_path: Optional[str] = None

        # Histórico
        self._history_limit = max(1, int(history_limit))
        self._back_stack: list[tuple[str, dict]] = []
        self._forward_stack: list[tuple[str, dict]] = []

    # -------------------------------------------------------------------------
    # Registro
    # -------------------------------------------------------------------------
    def register(self, path: str, widget: QWidget):
        """Registra uma página por caminho (pode conter '/')."""
        if not path or not isinstance(widget, QWidget):
            raise ValueError("Rota inválida ou widget inválido.")
        if path in self._pages:
            # último vence — mas é útil avisar no console em dev
            print(f"[WARN] sobrescrevendo rota já registrada: {path}")
        wrapped = self._ensure_scroller(widget)
        self._pages[path] = wrapped
        self.addWidget(wrapped)

    # --- Scroll wrapper automático ---
    def _ensure_scroller(self, w: QWidget) -> QWidget:
        try:
            if isinstance(w, QScrollArea):
                return w
            # Se a página já possui um QScrollArea interno, não embrulhar
            if w.findChild(QScrollArea) is not None:
                return w
            sa = QScrollArea()
            sa.setObjectName("PageScrollArea")
            sa.setFrameShape(QFrame.NoFrame)
            sa.setWidgetResizable(True)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            sa.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            # Manter gradiente do #FramelessFrame: viewport transparente
            try:
                sa.viewport().setAutoFillBackground(False)
            except Exception:
                pass

            # Conteúdo transparente igual ao Home: usa #FramelessContent e não pinta fundo
            content = QWidget()
            content.setObjectName("FramelessContent")
            content.setAttribute(Qt.WA_StyledBackground, False)
            lay = QVBoxLayout(content)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)
            try:
                w.setParent(content)
            except Exception:
                pass
            lay.addWidget(w)
            sa.setWidget(content)
            # Estabiliza largura: reserva margem quando vbar NÃO está visível; remove quando visível
            try:
                vb = sa.verticalScrollBar()
                vbw = max(8, vb.sizeHint().width())
                def _apply(*_args):
                    vis = vb.maximum() > 0
                    sa.setViewportMargins(0, 0, 0 if vis else vbw, 0)
                vb.rangeChanged.connect(_apply)
                _apply()
            except Exception:
                pass
            return sa
        except Exception:
            return w

    # -------------------------------------------------------------------------
    # Navegação "go" (empilha histórico)
    # -------------------------------------------------------------------------
    def go(self, path: str, params: Optional[dict] = None):
        """Navega para a rota (hierárquica) informada, empilhando histórico."""
        params = params or {}
        if path not in self._pages:
            raise KeyError(f"Rota '{path}' não registrada.")

        target = self._pages[path]

        # Empilha rota anterior no back_stack (se houver e se for diferente)
        if self._current_path is not None and self._current_path != path:
            self._back_stack.append((self._current_path, {}))
            # Limite do histórico
            if len(self._back_stack) > self._history_limit:
                self._back_stack.pop(0)
            # Ao navegar “fresh”, o forward é limpo
            self._forward_stack.clear()

        self.setCurrentWidget(target)

        old = self._current_path
        self._current_path = path

        # Hook DIP por página
        on_route = getattr(target, "on_route", None)
        if callable(on_route):
            try:
                on_route(params)
            except Exception as e:  # noqa: BLE001
                print(f"[WARN] on_route('{path}') falhou:", e)

        # Sinaliza mudança de rota + log simples
        try:
            self.routeChanged.emit(path, params)
            print("log.ui.navigate", {"from": old, "to": path, "ts": datetime.now().isoformat()})
        except Exception as e:
            print("[WARN] routeChanged emit falhou:", e)

    # -------------------------------------------------------------------------
    # Histórico (back/forward)
    # -------------------------------------------------------------------------
    def go_back(self) -> None:
        """Volta 1 passo no histórico, se possível."""
        if not self._back_stack:
            return
        current = (self._current_path, {}) if self._current_path else None
        path, params = self._back_stack.pop()
        if current and current[0] is not None:
            self._forward_stack.append(current)
        self._navigate_without_push(path, params)

    def go_forward(self) -> None:
        """Avança 1 passo no histórico, se possível."""
        if not self._forward_stack:
            return
        current = (self._current_path, {}) if self._current_path else None
        path, params = self._forward_stack.pop()
        if current and current[0] is not None:
            self._back_stack.append(current)
        self._navigate_without_push(path, params)

    def _navigate_without_push(self, path: str, params: dict):
        """Muda a página sem mexer no back/forward (uso interno)."""
        if path not in self._pages:
            return
        target = self._pages[path]
        self.setCurrentWidget(target)
        self._current_path = path

        on_route = getattr(target, "on_route", None)
        if callable(on_route):
            try:
                on_route(params or {})
            except Exception as e:
                print(f"[WARN] on_route('{path}') falhou:", e)

        try:
            self.routeChanged.emit(path, params or {})
            print("log.ui.navigate", {"from": None, "to": path, "ts": datetime.now().isoformat()})
        except Exception as e:
            print("[WARN] routeChanged emit falhou:", e)

    # -------------------------------------------------------------------------
    # API de leitura
    # -------------------------------------------------------------------------
    @property
    def current_route(self) -> Optional[str]:
        """Retorna o path da rota atual (ou None)."""
        return self._current_path
