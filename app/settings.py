# app/settings.py

from pathlib import Path
from typing import Optional
import shutil
import json
import re
import unicodedata


# ---------------------------------------------------------------------------
# Metadados do app
# ---------------------------------------------------------------------------
APP_TITLE = "Meu App"
DEFAULT_THEME = "Aku"
FIRST_PAGE = "home"
PAGES_MANIFEST_FILENAME = "pages_manifest.json"

# ---------------------------------------------------------------------------
# Pastas do pacote (somente leitura / assets empacotados)
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).resolve().parent
UI_DIR     = (BASE_DIR.parent / "ui").resolve()
APP_DIR    = (BASE_DIR.parent / "app").resolve()
ASSETS_DIR = (APP_DIR / "assets").resolve()
ICONS_DIR  = (ASSETS_DIR / "icons").resolve()
_ASSET_QSS_DIR    = (ASSETS_DIR / "qss").resolve()
_ASSET_THEMES_DIR = (ASSETS_DIR / "themes").resolve()

# ---------------------------------------------------------------------------
# Pastas internas graváveis (tudo dentro do projeto)
# ---------------------------------------------------------------------------
# Agora o app grava e lê temas, cache e qss diretamente de dentro do projeto.
THEMES_DIR   = (ASSETS_DIR / "themes").resolve()
CACHE_DIR    = (ASSETS_DIR / "cache").resolve()
USER_QSS_DIR = (ASSETS_DIR / "qss").resolve()

# ---------------------------------------------------------------------------
# Garantir diretórios
# ---------------------------------------------------------------------------
for _p in (THEMES_DIR, CACHE_DIR, USER_QSS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# BASE_QSS: prioriza arquivo local (se existir), caso contrário usa o de assets
# ---------------------------------------------------------------------------
_user_base_qss = USER_QSS_DIR / "base.qss"
_asset_base_qss = _ASSET_QSS_DIR / "base.qss"
BASE_QSS = _user_base_qss if _user_base_qss.exists() else _asset_base_qss

# ---------------------------------------------------------------------------
# Bootstrap de temas: copia temas de assets → pasta interna se estiver vazia
# ---------------------------------------------------------------------------
try:
    has_any_theme = any(THEMES_DIR.glob("*.json"))
    if (not has_any_theme) and _ASSET_THEMES_DIR.exists():
        for src in _ASSET_THEMES_DIR.glob("*.json"):
            dst = THEMES_DIR / src.name
            try:
                if str(src.resolve()) != str(dst.resolve()):  # evita copiar para si mesmo
                    shutil.copy2(src, dst)
            except Exception:
                pass
except Exception:
    # não interrompe o app se a cópia falhar
    pass

# ---------------------------------------------------------------------------
# Observações:
#  - Todos os módulos agora leem e escrevem direto nas pastas internas.
#  - Não há dependência de APPDATA, ~/.config, etc.
#  - A pasta do app precisa ser gravável (ok em dev ou se instalado no modo user).
# ---------------------------------------------------------------------------

# Helpers

def _slugify_theme(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # remove acentos
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s

def _read_exec_settings_theme() -> Optional[str]:
    # 1) Caminho via settings (preferível)
    json_path = None
    try:
        json_path = (CACHE_DIR / "_ui_exec_settings.json").resolve()
    except Exception:
        json_path = None

    # 2) Fallback: estrutura padrão do projeto (repo/app/assets/cache)
    if not json_path or not json_path.exists():
        here = Path(__file__).resolve()
        repo = here.parents[2] if len(here.parents) >= 3 else here.parent
        alt = (repo / "app" / "assets" / "cache" / "_ui_exec_settings.json")
        if alt.exists():
            json_path = alt.resolve()

    if not json_path or not json_path.exists():
        return None

    # 3) Ler o JSON com segurança
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        theme = data.get("theme")
        if isinstance(theme, str) and theme.strip():
            return theme.strip()
    except Exception:
        pass
    return None