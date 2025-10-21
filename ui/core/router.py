# ui/core/router.py

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QWidget


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
        self._pages[path] = widget
        self.addWidget(widget)

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
