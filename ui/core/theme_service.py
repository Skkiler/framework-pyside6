# ui/core/theme_service.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from PySide6.QtCore import QObject, Signal, QTimeLine, QFileSystemWatcher, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from ui.services.qss_renderer import load_base_qss, render_qss_from_base
from .settings import Settings
from .interface_ports import IThemeRepository
from ui.core.utils.helpers import is_hex, lerp_color, rgba_from_hex, coerce_vars, make_tokens


# =============================================================================
# Cache/QSS dump
# =============================================================================
@dataclass(frozen=True)
class _QssDump:
    dir: Path
    last_applied: Path

    @staticmethod
    def from_dir(cache_dir: Path) -> "_QssDump":
        cache_dir.mkdir(parents=True, exist_ok=True)
        return _QssDump(dir=cache_dir, last_applied=cache_dir / "last_applied.qss")


# =============================================================================
# ThemeService
# =============================================================================
class ThemeService(QObject):

    themeApplied = Signal(str)
    themesChanged = Signal(list)
    themeTokensChanged = Signal(dict)

    def __init__(
        self,
        repo: IThemeRepository,
        root: QWidget,
        settings: Optional[Settings] = None,
        base_qss_path: Optional[str] = None,
        animate_ms_default: int = 400,
        *,
        cache_dir: Optional[str | Path] = None,
    ):
        super().__init__(root)
        self._repo = repo
        self._root = root
        self._timeline: Optional[QTimeLine] = None
        self._current_name: Optional[str] = None
        self._animate_ms_default = max(80, int(animate_ms_default))
        self._qss_cache: dict[str, str] = {}
        self._last_qss_hash: Optional[int] = None
        self._themes_changed_debounce: Optional[QTimeLine] = None

        # QSS base (conteúdo do arquivo) + caminho (para watcher opcional)
        self._base_qss_path = Path(base_qss_path) if base_qss_path else None
        self._base_qss = load_base_qss(base_qss_path)

        # Cache (dump do QSS aplicado)
        cache_path = Path(cache_dir) if cache_dir else (Path.home() / ".ui_exec_cache")
        self._qss_dump = _QssDump.from_dir(cache_path)

        # Settings
        self._settings = settings or self._build_settings(cache_path)

        # File system watcher (pasta de temas e base.qss)
        self._watcher: Optional[QFileSystemWatcher] = None
        self._init_fs_watcher()

    # ------------------------------------------------------------------ factory
    def _build_settings(self, cache_dir: Path) -> Settings:
        try:
            return Settings(base_dir=str(cache_dir))
        except TypeError:
            # versão antiga
            return Settings()

    # ------------------------------- FS Watcher: inicialização e callbacks ----
    def _themes_dir(self) -> Optional[Path]:
        """
        Tenta descobrir a pasta dos temas a partir do repositório.
        Espera que o repo exponha 'theme_dir' (Path ou str). Se não houver, desabilita watcher.
        """
        td = getattr(self._repo, "theme_dir", "") or ""
        if not td:
            return None
        try:
            p = Path(td)
            return p if p.exists() and p.is_dir() else None
        except Exception:
            return None

    def _init_fs_watcher(self) -> None:
        """Observa alterações na pasta de temas e nos arquivos .json individuais."""
        try:
            self._watcher = QFileSystemWatcher(self)
        except Exception:
            self._watcher = None
            return

        # Observa pasta/arquivos de temas
        tdir = self._themes_dir()
        if tdir:
            try:
                self._watcher.addPath(str(tdir))
            except Exception:
                pass
            # também observa cada .json para pegar salva/edita sem mtime de diretório
            for f in tdir.glob("*.json"):
                try:
                    self._watcher.addPath(str(f))
                except Exception:
                    pass

        # Observa o base.qss, se houver caminho
        if self._base_qss_path and self._base_qss_path.exists():
            try:
                self._watcher.addPath(str(self._base_qss_path))
            except Exception:
                pass

        if self._watcher:
            self._watcher.directoryChanged.connect(self._on_fs_changed)
            self._watcher.fileChanged.connect(self._on_fs_changed)

    def _resubscribe_theme_files(self) -> None:
        if not self._watcher:
            return
        tdir = self._themes_dir()
        if not tdir:
            return

        try:
            current_files = set(self._watcher.files())
        except Exception:
            current_files = set()

        # (novo) garante que o diretório está inscrito
        try:
            if str(tdir) not in current_files and tdir.exists():
                self._watcher.addPath(str(tdir))
        except Exception:
            pass

        # Adiciona novos .json
        try:
            for f in tdir.glob("*.json"):
                sf = str(f)
                if sf not in current_files:
                    try:
                        self._watcher.addPath(sf)
                    except Exception:
                        pass
        except Exception:
            pass

        # Remove paths que não existem mais
        try:
            for sf in list(current_files):
                if sf.endswith(".json") and not Path(sf).exists():
                    try:
                        self._watcher.removePath(sf)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_fs_changed(self, _path: str) -> None:
        """
        Disparado quando:
          - um .json é criado/editado/excluído
          - a pasta de temas muda
          - (opcional) o base.qss muda
        """
        # 1) Se foi o base.qss, recarrega e reaplica tema atual
        if self._base_qss_path and _path and Path(_path) == self._base_qss_path:
            self.reload_base_qss(str(self._base_qss_path))
            if self._current_name:
                cur = self._safe_load_theme(self._current_name)
                if cur:
                    self._apply_now(cur, dump=False)
                    self.themeApplied.emit(self._current_name)
            # não retorna; pode também ter alterado temas

        # 2) Atualiza lista de temas (para criação/exclusão/renomeio)
        try:
            self.themesChanged.emit(self.available())
        except Exception:
            pass

        # 3) Se o arquivo do tema atual mudou (ou foi removido/alterado), tenta recarregar
        if self._current_name:
            try:
                new = self._repo.load_theme(self._current_name)
                if isinstance(new, dict):
                    # aplica sem animação para ser instantâneo
                    self._apply_now(new, dump=False)
                    self.themeApplied.emit(self._current_name)
                    self._broadcast_tokens(new)
            except Exception:
                # silencia: arquivo pode ter sido removido; mantém UI estável
                pass

        # 4) Reinscreve arquivos (captura novos .json e retira os que sumiram)
        self._resubscribe_theme_files()

    # ------------------------------------------------------------------- public
    def available(self) -> list[str]:
        return self._repo.list_themes()

    def current(self) -> Optional[str]:
        return self._current_name

    def load_selected_from_settings(self) -> Optional[str]:
        return self._settings.read("theme", None)

    def reload_base_qss(self, base_qss_path: Optional[str]) -> None:
        """Permite recarregar o base.qss em runtime (ex.: dev troca arquivo)."""
        self._base_qss_path = Path(base_qss_path) if base_qss_path else None
        self._base_qss = load_base_qss(base_qss_path)

    def save_theme(self, name: str, data: Dict[str, Any]) -> None:
        self._repo.save_theme(name, data)

        try:
            if hasattr(self._repo, "theme_dir"):
                from os.path import exists, join
                if not exists(join(getattr(self._repo, "theme_dir"), f"{name}.json")):
                    print(f"[WARN] save_theme: {name}.json não apareceu no FS esperado.")
        except Exception:
            pass

        self.themesChanged.emit(self.available())
        self._resubscribe_theme_files()

    def delete_theme(self, name: str) -> None:
        self._repo.delete_theme(name)
        try:
            if hasattr(self._repo, "theme_dir"):
                from os.path import exists, join
                if exists(join(getattr(self._repo, "theme_dir"), f"{name}.json")):
                    print(f"[WARN] delete_theme: {name}.json ainda existe após remover.")
        except Exception:
            pass

        self.themesChanged.emit(self.available())
        if self._watcher:
            tdir = self._themes_dir()
            if tdir:
                sf = str(tdir / f"{name}.json")
                try:
                    self._watcher.removePath(sf)
                except Exception:
                    pass

    def load_theme(self, name: str) -> Dict[str, Any]:
        """Leitura via repo (helper para evitar acessar _repo fora)."""
        return self._repo.load_theme(name)

    def apply(
        self,
        theme_name: str,
        animate: bool = True,
        persist: bool = True,
        duration_ms: Optional[int] = None,
    ) -> None:
        """
        Aplica um tema. Se `animate=True` e há tema anterior, interpola cores hex.
        """
        # Short‑circuit when applying the same theme again
        if theme_name and self._current_name and theme_name == self._current_name:
            return

        new_theme = self._safe_load_theme(theme_name)
        if new_theme is None:
            return

        old_theme = self._safe_load_theme(self._current_name) if self._current_name else None

        # se o root suporta "heavy anim", liga/desliga durante transição
        begin_heavy: Optional[Callable[[], None]] = getattr(self._root, "_begin_heavy_anim", None)
        end_heavy:   Optional[Callable[[], None]] = getattr(self._root, "_end_heavy_anim", None)

        try:
            if callable(begin_heavy):
                begin_heavy()

            if animate and old_theme:
                self._animate_apply(old_theme, new_theme, duration_ms or self._animate_ms_default)
            else:
                self._apply_now(new_theme, cache_key=theme_name)

            self._current_name = theme_name
            if persist:
                self._settings.write("theme", theme_name)
            self.themeApplied.emit(theme_name)
        finally:
            # se houver animação, end_heavy será chamado no finished() também,
            # mas chamamos aqui como salvaguarda.
            if not self._timeline and callable(end_heavy):
                end_heavy()

    # ------------------------------------------------------------------ internals
    def _safe_load_theme(self, name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        try:
            data = self._repo.load_theme(name)
            return data if isinstance(data, dict) else None
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] Falha ao carregar tema '{name}': {e}")
            return None

    def _broadcast_tokens(self, vars_or_theme: Dict[str, Any]) -> None:
        """Emite tokens já derivados, para quem precisar 'repintar' recursos."""
        vars_map = coerce_vars(vars_or_theme)
        tokens = make_tokens(vars_map)
        self.themeTokensChanged.emit(tokens)

    def _apply_palette_min(self, theme: Dict[str, Any]) -> None:
        """Aplica apenas roles informados no tema (não ‘reseta’ tudo)."""
        app = QApplication.instance()
        if not app:
            return
        palette_map = theme.get("palette") or {}
        if not isinstance(palette_map, dict):
            return

        pal = QPalette(app.palette())
        for role_name, hex_color in palette_map.items():
            if hasattr(QPalette, role_name) and is_hex(hex_color):
                pal.setColor(getattr(QPalette, role_name), QColor(hex_color))
        app.setPalette(pal)

    def apply_theme_interpolated(self, start_tokens: dict, end_tokens: dict, steps: int = 28):
        """
        Interpola os tokens do tema em pequenos passos e aplica o QSS ao final.
        """
        self._interpolation_step = 0
        self._interpolation_steps = steps
        self._start_tokens = start_tokens
        self._end_tokens = end_tokens
        self._interpolated_tokens = dict(start_tokens)
        self._timer = QTimer(self)
        interval = max(8, int(self._animate_ms_default / steps))
        self._timer.timeout.connect(self._interpolation_tick)
        self._timer.start(interval)

    def _interpolation_tick(self):
        t = self._interpolation_step / self._interpolation_steps
        for k in self._start_tokens:
            v0 = self._start_tokens[k]
            v1 = self._end_tokens.get(k, v0)
            if is_hex(v0) and is_hex(v1):
                c0 = QColor(v0)
                c1 = QColor(v1)
                c = lerp_color(c0, c1, t)
                self._interpolated_tokens[k] = c.name(QColor.HexArgb)
            else:
                self._interpolated_tokens[k] = v1 if t > 0.5 else v0
        self._interpolation_step += 1
        if self._interpolation_step > self._interpolation_steps:
            self._timer.stop()
            self._apply_qss(self._interpolated_tokens)

    def _apply_qss(self, tokens: dict):
        qss = render_qss_from_base(self._base_qss, tokens)
        self._root.setStyleSheet(qss)

    def _apply_qss(self, theme: Dict[str, Any], *, dump: bool = False, cache_key: Optional[str] = None) -> None:
        """Aplica QSS completo. Opcionalmente grava dump em disco (custa caro)."""
        vars_map = coerce_vars(theme)
        tokens = make_tokens(vars_map)

        # Cache QSS by key (theme name) to avoid full render on repeated applies
        qss: Optional[str] = None
        if cache_key:
            qss = self._qss_cache.get(cache_key)
        if not qss:
            qss = render_qss_from_base(
                self._base_qss,
                tokens,
                debug_dump_path=str(self._qss_dump.last_applied) if dump else None,
            )
            if cache_key:
                self._qss_cache[cache_key] = qss

        # Apply on the root window; stylesheet propagates to children
        try:
            if self._root:
                self._root.setStyleSheet(qss)
            # Also apply at application level so floating top-levels (e.g., Toast) inherit
            app = QApplication.instance()
            if app is not None:
                try:
                    app.setStyleSheet(qss)
                except Exception:
                    # fallback defensivo
                    pass
        except Exception:
            pass

        # notify tokens for icon re-renderers
        self.themeTokensChanged.emit(tokens)

    def _apply_qss_light(self, vars_only: Dict[str, Any]) -> None:
        app = QApplication.instance()
        if not app:
            return
        tokens = make_tokens(vars_only)
        qss = render_qss_from_base(self._base_qss, tokens)
        try:
            # >>> antes: app.setStyleSheet(qss)
            self._root.setStyleSheet(qss)
        except Exception:
            pass
        finally:
            # durante animação: broadcast dos tokens mixados (pra re-rasterizar ícones, etc.)
            self.themeTokensChanged.emit(tokens)


    def _apply_now(self, theme: Dict[str, Any], *, dump: bool = False, cache_key: Optional[str] = None) -> None:
        try:
            if self._root and self._root.styleSheet():
                self._root.setStyleSheet("")   # <- limpa override local
                self._root.style().unpolish(self._root)
                self._root.style().polish(self._root)
                # Após limpar, resetamos o hash para garantir re-aplicação
                self._last_qss_hash = None
        except Exception:
            pass

        self._apply_palette_min(theme)
        self._apply_qss(theme, dump=dump, cache_key=cache_key)

    def _animate_apply(self, old: Dict[str, Any], new: Dict[str, Any], ms: int) -> None:
        if self._timeline:
            try:
                self._timeline.stop()
            except Exception:
                pass
            self._timeline = None

        self._timeline = QTimeLine(max(80, int(ms)), self)
        self._timeline.setFrameRange(0, 100)
        self._timeline.setUpdateInterval(33)  # ~30 FPS para reduzir custo

        old_vars = coerce_vars(old)
        new_vars = coerce_vars(new)

        keys = {
            k for k in (old_vars.keys() & new_vars.keys())
            if is_hex(old_vars[k]) and is_hex(new_vars[k])
        }

        end_heavy: Optional[Callable[[], None]] = getattr(self._root, "_end_heavy_anim", None)

        def _frame_changed(i: int):
            t = i / 100.0
            mix_vars = dict(new_vars)
            for k in keys:
                ca, cb = QColor(old_vars[k]), QColor(new_vars[k])
                mix_vars[k] = lerp_color(ca, cb, t).name(
                    QColor.HexArgb if (ca.alpha() != 255 or cb.alpha() != 255) else QColor.HexRgb
                )
            # aplica somente no ROOT durante a animação
            self._apply_qss_light(mix_vars)

        def _finished():
            try:
                try:
                    if self._root and self._root.styleSheet():
                        self._root.setStyleSheet("")   # <- limpa override local
                        self._root.style().unpolish(self._root)
                        self._root.style().polish(self._root)
                except Exception:
                    pass

                self._apply_now(new, dump=True)
            finally:
                if callable(end_heavy):
                    end_heavy()
                self._timeline = None

        self._timeline.frameChanged.connect(_frame_changed)
        self._timeline.finished.connect(_finished)
        self._timeline.start()
