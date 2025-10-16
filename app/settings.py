from pathlib import Path
import shutil

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
ASSETS_DIR = (UI_DIR / "assets").resolve()
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
