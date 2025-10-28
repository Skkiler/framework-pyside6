from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtGui import QIcon

class ResourceManager:
    """
    Gerenciador de recursos da aplicação seguindo o princípio da Responsabilidade Única (SRP).
    """
    def __init__(self, assets_dir: str | Path):
        self.assets_dir = Path(assets_dir)
        self.cache_dir = self._ensure_dir(self.assets_dir / "cache")
        self.icons_dir = self.assets_dir / "icons"
        self.themes_dir = self.assets_dir / "themes"
        self.qss_dir = self.assets_dir / "qss"
        
    def _ensure_dir(self, path: Path) -> Path:
        """Garante que um diretório existe."""
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_icon(self, name: str, category: Optional[str] = None) -> Optional[QIcon]:
        """
        Obtém um ícone do diretório de ícones.
        
        Args:
            name: Nome do arquivo do ícone
            category: Subdiretório opcional onde o ícone está localizado
        """
        if not name.endswith(('.ico', '.png', '.svg')):
            name = f"{name}.png"  # extensão padrão
            
        icon_path = self.icons_dir
        if category:
            icon_path = icon_path / category
            
        icon_file = icon_path / name
        return QIcon(str(icon_file)) if icon_file.exists() else None
    
    def get_theme_path(self, theme_name: str) -> Path:
        """Retorna o caminho para um arquivo de tema."""
        return self.themes_dir / f"{theme_name}.json"
    
    def get_qss_path(self, name: str = "base") -> Path:
        """Retorna o caminho para um arquivo QSS."""
        return self.qss_dir / f"{name}.qss"
    
    def get_cache_path(self, name: str) -> Path:
        """Retorna um caminho no diretório de cache."""
        return self.cache_dir / name
