# ui/core/theme_service.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from PySide6.QtCore import QObject, Signal, QTimeLine, QFileSystemWatcher, QTimer, QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QGraphicsOpacityEffect

from ui.services.qss_renderer import load_base_qss, render_qss_from_base, clear_anim_qss_cache
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
        self._timeline: Optional[QPropertyAnimation] = None
        self._current_name: Optional[str] = None
        self._animate_ms_default = max(80, int(animate_ms_default))
        self._qss_cache: dict[str, str] = {}
        self._last_qss_hash: Optional[int] = None
        self._themes_changed_debounce: Optional[QTimeLine] = None
        self._crossfade_overlay: Optional[QWidget] = None
        self._crossfade_effect: Optional[QGraphicsOpacityEffect] = None

        # Métricas e throttle; habilite _debug_log_stylesheet_counts manualmente
        # para exibir contagens ao final de cada animação.
        self._debug_log_stylesheet_counts: bool = False
        # Contagem de setStyleSheet no root/app durante uma animação:
        self._ss_counts: dict[str, int] = {"root": 0, "app": 0}
        # Timestamp da última aplicação de QSS (p/ throttle ~60 FPS):
        self._last_apply_ts: float = 0.0
        # Timestamp do último broadcast de tokens (≤ 15 Hz):
        self._last_token_broadcast: float = 0.0
        # Flag indicando se há animação pesada em andamento:
        self._is_heavy_anim: bool = False

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

        self._cancel_inflight_animation(end_heavy)

        try:
            if callable(begin_heavy):
                begin_heavy()
            # Marca heavy anim internamente quando houver interpolação
            self._is_heavy_anim = bool(animate and old_theme)

            if animate and old_theme:
                # guarda nome para efetivar ao final: só atualiza _current_name no finished()
                self._pending_persist = bool(persist)
                self._pending_theme_name = theme_name
                self._animate_apply(old_theme, new_theme, duration_ms or self._animate_ms_default)
            else:
                # aplicação imediata: tema final completo e persistência
                if hasattr(self, "_pending_persist"):
                    try:
                        delattr(self, "_pending_persist")
                    except Exception:
                        pass
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

    def apply_theme_interpolated(self, start_tokens: dict, end_tokens: dict, steps: int = 60):
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
            # Caminho legado: aplica tokens no root (leve)
            self._apply_qss_tokens(self._interpolated_tokens)

    # --------------- Nova lógica de QSS ---------------
    def _apply_qss_tokens(self, vars_only: Dict[str, Any]) -> None:
        """Aplica QSS leve durante animação.
        - Converte vars em tokens e usa render_qss_from_base.
        - Throttle setStyleSheet: aplica no root apenas se decorreu ≥ _anim_min_interval_s.
        - Limita emissões de themeTokensChanged a ≤ 15 Hz.
        """
        app = QApplication.instance()
        if not app:
            return
        import time
        now = time.monotonic()
        min_interval = getattr(self, "_anim_min_interval_s", 0.016)  # ~60 FPS
        last_apply_delta = (now - self._last_apply_ts) if self._last_apply_ts else None
        need_apply = last_apply_delta is None or last_apply_delta >= float(min_interval)
        need_emit = (now - self._last_token_broadcast) > 0.066

        if not need_apply and not need_emit:
            return

        tokens = make_tokens(coerce_vars(vars_only))

        if not need_apply:
            # Apenas broadcast para ícones/observadores sem aplicar QSS completo
            self._last_token_broadcast = now
            try:
                self.themeTokensChanged.emit(tokens)
            except Exception:
                pass
            return

        qss = render_qss_from_base(self._base_qss, tokens)
        self._last_apply_ts = now
        try:
            if self._root:
                self._root.setStyleSheet(qss)
                self._ss_counts["root"] = self._ss_counts.get("root", 0) + 1
        except Exception:
            pass
        finally:
            if (now - self._last_token_broadcast) > 0.066:
                self._last_token_broadcast = now
                try:
                    self.themeTokensChanged.emit(tokens)
                except Exception:
                    pass

    def _apply_qss_full(self, theme: Dict[str, Any], *, dump: bool = False,
                        cache_key: Optional[str] = None) -> None:
        """Aplica QSS completo fora da animação. Usa cache por nome do tema."""
        vars_map = coerce_vars(theme)
        tokens = make_tokens(vars_map)
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
        try:
            if self._root:
                self._root.setStyleSheet(qss)
                self._ss_counts["root"] = self._ss_counts.get("root", 0) + 1
            app = QApplication.instance()
            if app is not None:
                app.setStyleSheet(qss)
                self._ss_counts["app"] = self._ss_counts.get("app", 0) + 1
        except Exception:
            pass
        self.themeTokensChanged.emit(tokens)

    def _apply_qss_light(self, vars_only: Dict[str, Any]) -> None:
        """Compat: aplica tokens de forma leve delegando para _apply_qss_tokens."""
        self._apply_qss_tokens(vars_only)

    def _apply_now(self, theme: Dict[str, Any], *, dump: bool = False,
                   cache_key: Optional[str] = None) -> None:
        """Aplicação final: limpa overrides, reseta caches leves e aplica QSS completo."""
        try:
            if self._root and self._root.styleSheet():
                self._root.setStyleSheet("")
                self._root.style().unpolish(self._root)
                self._root.style().polish(self._root)
                self._last_qss_hash = None
        except Exception:
            pass
        try:
            clear_anim_qss_cache()
        except Exception:
            pass
        self._apply_palette_min(theme)
        self._apply_qss_full(theme, dump=dump, cache_key=cache_key)
        if self._debug_log_stylesheet_counts:
            try:
                print(f"[ThemeService][apply_now] setStyleSheet root={self._ss_counts.get('root',0)} app={self._ss_counts.get('app',0)}")
            except Exception:
                pass
            finally:
                self._ss_counts = {"root": 0, "app": 0}

    def _finalize_pending_theme(self, *, end_heavy: Optional[Callable[[], None]] = None) -> None:
        """Efetiva o tema pendente, persiste e emite sinais após animação."""
        try:
            pending = getattr(self, "_pending_theme_name", None)
            if pending:
                self._current_name = pending
                if bool(getattr(self, "_pending_persist", False)):
                    try:
                        self._settings.write("theme", pending)
                    except Exception:
                        pass
                self.themeApplied.emit(pending)
                delattr(self, "_pending_theme_name")
        except Exception:
            pass
        finally:
            if hasattr(self, "_pending_persist"):
                try:
                    delattr(self, "_pending_persist")
                except Exception:
                    pass
            self._last_apply_ts = 0.0
            self._last_token_broadcast = 0.0
            self._is_heavy_anim = False
            try:
                delattr(self, "_anim_min_interval_s")
            except Exception:
                pass
            if self._debug_log_stylesheet_counts:
                try:
                    print(f"[ThemeService][anim_end] setStyleSheet root={self._ss_counts.get('root',0)} app={self._ss_counts.get('app',0)}")
                except Exception:
                    pass
                finally:
                    self._ss_counts = {"root": 0, "app": 0}
            else:
                self._ss_counts = {"root": 0, "app": 0}
            if callable(end_heavy):
                try:
                    end_heavy()
                except Exception:
                    pass

    def _cancel_inflight_animation(self, end_heavy: Optional[Callable[[], None]] = None) -> None:
        """Interrompe animação em andamento e finaliza estado pendente."""
        if self._timeline:
            try:
                self._timeline.stop()
            except Exception:
                pass
            self._timeline = None
        overlay = self._crossfade_overlay
        if overlay is not None:
            try:
                overlay.hide()
            except Exception:
                pass
            try:
                overlay.deleteLater()
            except Exception:
                pass
            self._crossfade_overlay = None
            self._crossfade_effect = None
        if hasattr(self, "_pending_theme_name"):
            self._finalize_pending_theme(end_heavy=end_heavy)
        elif callable(end_heavy):
            try:
                end_heavy()
            except Exception:
                pass

    def _animate_apply(self, old: Dict[str, Any], new: Dict[str, Any], ms: int) -> None:
        """Executa crossfade entre temas, aplicando o novo e esmaecendo o anterior."""
        root = self._root
        end_heavy: Optional[Callable[[], None]] = getattr(root, "_end_heavy_anim", None) if root else None

        duration_eff = max(160, int(ms))

        pixmap = None
        if root and root.isVisible():
            try:
                pixmap = root.grab()
            except Exception:
                pixmap = None

        if pixmap is None or pixmap.isNull():
            self._apply_now(new, dump=True, cache_key=getattr(self, "_pending_theme_name", None))
            self._finalize_pending_theme(end_heavy=end_heavy)
            return

        self._is_heavy_anim = True
        self._apply_now(new, dump=True, cache_key=getattr(self, "_pending_theme_name", None))

        overlay = QLabel(root) if root else None
        if overlay is None:
            self._finalize_pending_theme(end_heavy=end_heavy)
            return
        overlay.setPixmap(pixmap)
        overlay.setGeometry(root.rect())
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        overlay.setStyleSheet('background: transparent; border: 0;')
        overlay.raise_()
        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(1.0)
        overlay.setGraphicsEffect(effect)
        overlay.show()

        anim = QPropertyAnimation(effect, b"opacity", overlay)
        anim.setDuration(duration_eff)
        try:
            anim.setEasingCurve(QEasingCurve.InOutCubic)
        except Exception:
            pass
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)

        self._crossfade_overlay = overlay
        self._crossfade_effect = effect
        self._timeline = anim

        def _cleanup() -> None:
            try:
                overlay.hide()
            except Exception:
                pass
            try:
                overlay.deleteLater()
            except Exception:
                pass
            self._crossfade_overlay = None
            self._crossfade_effect = None
            self._timeline = None
            self._finalize_pending_theme(end_heavy=end_heavy)

        anim.finished.connect(_cleanup)
        anim.start()

