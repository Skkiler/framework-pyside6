from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, TypeVar
from PySide6.QtWidgets import QWidget

T = TypeVar('T')

class PageFactory(Protocol):
    """Protocolo para factories de páginas."""
    def __call__(self, **kwargs: Any) -> QWidget:
        ...

class PageManager:
    """
    Gerenciador de páginas que segue o princípio da Responsabilidade Única (SRP).
    Lida com o registro e criação de páginas.
    """
    
    def __init__(self):
        self._factories: Dict[str, PageFactory] = {}
        self._dependencies: Dict[str, Dict[str, Any]] = {}
        
    def register(self, page_id: str, factory: PageFactory, **dependencies: Any) -> None:
        """
        Registra uma factory de página com suas dependências.
        
        Args:
            page_id: Identificador único da página
            factory: Função factory que cria a página
            **dependencies: Dependências necessárias para criar a página
        """
        self._factories[page_id] = factory
        self._dependencies[page_id] = dependencies
        
    def create(self, page_id: str, **extra_deps: Any) -> Optional[QWidget]:
        """
        Cria uma instância de página usando a factory registrada.
        
        Args:
            page_id: Identificador da página
            **extra_deps: Dependências adicionais para esta instância
        """
        if page_id not in self._factories:
            return None
            
        # Combina dependências registradas com extras
        deps = self._dependencies[page_id].copy()
        deps.update(extra_deps)
        
        # Cria a página usando apenas as dependências que a factory aceita
        factory = self._factories[page_id]
        return factory(**deps)
        
    def has_page(self, page_id: str) -> bool:
        """Verifica se uma página está registrada."""
        return page_id in self._factories
        
    @property
    def available_pages(self) -> list[str]:
        """Lista de páginas disponíveis."""
        return list(self._factories.keys())
