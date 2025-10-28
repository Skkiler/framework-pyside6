from __future__ import annotations

from typing import Any, Dict, Optional
from pathlib import Path
import json
from abc import ABC, abstractmethod

class SettingsProvider(ABC):
    """Interface para provedores de configurações seguindo o princípio da Inversão de Dependência (DIP)."""
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Carrega as configurações."""
        pass
    
    @abstractmethod
    def save(self, settings: Dict[str, Any]) -> None:
        """Salva as configurações."""
        pass

class JsonSettingsProvider(SettingsProvider):
    """Implementação de configurações usando JSON."""
    
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
    def load(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
            
    def save(self, settings: Dict[str, Any]) -> None:
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)

class Settings:
    """
    Gerenciador de configurações que segue o princípio Open/Closed.
    Novas fontes de configuração podem ser adicionadas sem modificar esta classe.
    """
    
    def __init__(self, provider: SettingsProvider):
        self._provider = provider
        self._settings = provider.load()
        self._defaults: Dict[str, Any] = {}
        
    def register_defaults(self, defaults: Dict[str, Any]) -> None:
        """Registra valores padrão para configurações."""
        self._defaults.update(defaults)
        
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém uma configuração, usando o valor padrão registrado se disponível."""
        return self._settings.get(key, self._defaults.get(key, default))
        
    def set(self, key: str, value: Any) -> None:
        """Define uma configuração e salva automaticamente."""
        self._settings[key] = value
        self._provider.save(self._settings)
        
    def update(self, settings: Dict[str, Any]) -> None:
        """Atualiza múltiplas configurações de uma vez."""
        self._settings.update(settings)
        self._provider.save(self._settings)
        
    @property
    def all(self) -> Dict[str, Any]:
        """Retorna todas as configurações."""
        return self._settings.copy()
