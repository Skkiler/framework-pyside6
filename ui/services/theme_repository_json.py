# ui/services/theme_repository_json.py

import json, os, tempfile, platform
from typing import List, Dict, Any
from ..core.interface_ports import IThemeRepository

def _ensure_dir(p: str) -> str:
    ap = os.path.abspath(p)
    os.makedirs(ap, exist_ok=True)
    return ap

def _fsync_dir(path: str) -> None:

    if os.name != "posix":
        return  # no-op no Windows
    try:
        dir_fd = os.open(path, os.O_DIRECTORY)  # type: ignore[attr-defined]
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        # melhor não quebrar fluxo por causa de fsync do diretório
        pass

class JsonThemeRepository(IThemeRepository):
    def __init__(self, theme_dir: str):
        # Caminho ABSOLUTO e garantidamente existente
        self.theme_dir = _ensure_dir(theme_dir)

    def _path(self, name: str) -> str:
        return os.path.join(self.theme_dir, f"{name}.json")

    def list_themes(self) -> List[str]:
        if not os.path.exists(self.theme_dir):
            return []
        return sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(self.theme_dir)
            if f.endswith(".json")
        )

    def load_theme(self, name: str) -> Dict[str, Any]:
        with open(self._path(name), "r", encoding="utf-8") as f:
            return json.load(f)

    def save_theme(self, name: str, data: Dict[str, Any]) -> None:
        """
        Gravação ATÔMICA + fsync do ARQUIVO.
        (No Windows, pulamos fsync do diretório; no POSIX, fazemos.)
        """
        dpath = _ensure_dir(self.theme_dir)
        final_path = self._path(name)

        fd, tmp_path = tempfile.mkstemp(prefix=f".{name}.", suffix=".json.tmp", dir=dpath)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # força disco (funciona no Windows/Posix)

            os.replace(tmp_path, final_path)  # atômico no mesmo volume
            _fsync_dir(dpath)  # no-op no Windows; efetivo no POSIX
        finally:
            # Se falhar antes do replace, tenta remover tmp
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def delete_theme(self, name: str) -> None:
        fp = self._path(name)
        if os.path.exists(fp):
            os.remove(fp)
            _fsync_dir(self.theme_dir)  # no-op no Windows
