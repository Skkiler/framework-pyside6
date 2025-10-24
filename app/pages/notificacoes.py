# app/pages/notificacoes.py

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime
import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QEvent, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QFrame, QListView
)

from ui.widgets.toast import notification_bus
from ui.widgets.push_sidebar import PushSidePanel


PAGE = {
    "route": "notificacoes",
    "label": "Notificações",
    "sidebar": False,
    "order": 50,
}

# ------------------------- Item da lista -------------------------

class _Row(QWidget):
    """Linha compacta: apenas 'Título – HH:MM:SS' (com quebra)."""
    sizeChanged = Signal()

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self._entry = dict(entry or {})

        # Vamos estilizar o pill diretamente neste widget
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("NotificationRow")

        root = QVBoxLayout(self)
        # margens simétricas => texto centralizado verticalmente no pill
        root.setContentsMargins(14, 8, 14, 8)
        root.setSpacing(0)

        self._header = QLabel(self._fmt_header(self._entry), self)
        f = self._header.font()
        f.setBold(True)
        self._header.setFont(f)
        self._header.setWordWrap(True)
        self._header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._header.setMargin(0)
        root.addWidget(self._header)

        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._sync_heights()

    def changeEvent(self, ev):
        if ev.type() in (QEvent.FontChange, QEvent.StyleChange, QEvent.PaletteChange):
            self._sync_heights()
        return super().changeEvent(ev)

    def _sync_heights(self):
        """Ajusta a altura mínima baseado na largura, para o pill abraçar o texto."""
        layout = self.layout()
        lm = layout.contentsMargins()
        avail_w = max(0, self.width() - (lm.left() + lm.right()))
        if avail_w <= 0:
            avail_w = max(0, self._header.width())

        if self._header.hasHeightForWidth():
            h = self._header.heightForWidth(avail_w)
        else:
            h = self._header.sizeHint().height()

        if h <= 0:
            h = self._header.sizeHint().height()

        self._header.setMinimumHeight(h)
        total_h = h + (lm.top() + lm.bottom())
        self.setMinimumHeight(total_h)
        self.updateGeometry()
        self.sizeChanged.emit()

    def resizeEvent(self, ev):
        self._sync_heights()
        return super().resizeEvent(ev)

    def mousePressEvent(self, ev):
        ev.ignore()  # quem trata é o QListWidget
        return super().mousePressEvent(ev)

    def _fmt_header(self, entry: dict) -> str:
        title = (entry.get("title") or "Notificação").strip()
        ts = entry.get("_ts_str") or datetime.now().strftime("%H:%M:%S")
        return f"{title} – {ts}"

    def update_from(self, entry: dict):
        self._entry.update(entry or {})
        self._header.setText(self._fmt_header(self._entry))
        self._sync_heights()


# ------------------------- Painel de Detalhes -------------------------

class _DetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_id: Optional[str] = None
        self._entry: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._title = QLabel("Detalhes", self)
        ft = self._title.font(); ft.setBold(True); ft.setPointSize(11)
        self._title.setFont(ft); self._title.setWordWrap(True)
        root.addWidget(self._title)

        self._lbl_id = QLabel("", self);    self._lbl_id.setWordWrap(True)
        self._lbl_type = QLabel("", self);  self._lbl_type.setWordWrap(True)
        self._lbl_time = QLabel("", self);  self._lbl_time.setWordWrap(True)
        self._lbl_flags = QLabel("", self); self._lbl_flags.setWordWrap(True)

        for w in (self._lbl_id, self._lbl_type, self._lbl_time, self._lbl_flags):
            w.setTextInteractionFlags(Qt.TextSelectableByMouse)
            root.addWidget(w)

        self._body = QLabel("", self)
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self._body, 1)

        actions = QHBoxLayout(); actions.setSpacing(6)
        self._btn_finish = QPushButton("Concluir")
        self._btn_finish.setProperty("variant", "chip")
        self._btn_finish.setProperty("size", "sm")
        actions.addWidget(self._btn_finish); actions.addStretch(1)
        root.addLayout(actions)

        bus = notification_bus()
        self._btn_finish.clicked.connect(lambda: self._emit_finish(bus))

    def set_entry(self, entry: Optional[dict]):
        self._entry = dict(entry or {})
        self._current_id = str(self._entry.get("id") or "") or None
        self._refresh()

    def current_id(self) -> Optional[str]:
        return self._current_id

    def _refresh(self):
        e = self._entry or {}
        _id = e.get("id") or ""
        t = e.get("title") or "Notificação"
        typ = e.get("type", "info")
        ts = e.get("_ts_str") or ""
        finished = bool(e.get("finished", False))
        persist = bool(e.get("persist", False))
        expires = bool(e.get("expires_on_finish", True))
        txt = e.get("text") or ""

        self._title.setText(t)
        self._lbl_id.setText(f"<b>ID:</b> { _id }")
        self._lbl_type.setText(f"<b>Tipo:</b> { typ }")
        self._lbl_time.setText(f"<b>Horário:</b> { ts }")
        flags = []
        flags.append("concluída" if finished else "pendente")
        flags.append("persistente" if persist else "não persistente")
        flags.append("expira ao concluir" if expires else "não expira ao concluir")
        self._lbl_flags.setText("<b>Estado:</b> " + " · ".join(flags))
        self._body.setText(txt)

        self._btn_finish.setEnabled(bool(_id))

    def _emit_finish(self, bus):
        if self._current_id:
            try:
                bus.finishEntry.emit(self._current_id)
            except Exception:
                pass


# ------------------------- Centro de Notificações -------------------------

class NotificationCenter(QWidget):
    countChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotificationCenter")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._entries: Dict[str, dict] = {}
        self._items: Dict[str, QListWidgetItem] = {}

        self._storage_path = self._resolve_storage_path()

        # ----- LAYOUT RAIZ (com sidebar) -----
        rootH = QHBoxLayout(self)
        rootH.setContentsMargins(8, 8, 8, 8)
        rootH.setSpacing(8)

        # ----- COLUNA PRINCIPAL -----
        main = QFrame(self)
        main.setObjectName("NotificationMain")
        main.setAttribute(Qt.WA_StyledBackground, True)
        main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rootH.addWidget(main, 1)

        root = QVBoxLayout(main)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        panel = QFrame(main)
        panel.setObjectName("NotificationPanel")
        panel.setAttribute(Qt.WA_StyledBackground, True)
        root.addWidget(panel)

        pnl = QVBoxLayout(panel)
        pnl.setContentsMargins(10, 10, 10, 10)
        pnl.setSpacing(8)

        header_wrap = QVBoxLayout()
        header_wrap.setContentsMargins(0, 0, 0, 0)
        header_wrap.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(1)

        title = QLabel("Centro de Notificações", panel)
        f = title.font(); f.setBold(True); f.setPointSize(12)
        title.setFont(f)
        title_row.addWidget(title)
        title_row.addStretch(1)
        header_wrap.addLayout(title_row)

        actions_row = QHBoxLayout()
        actions_row.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self._btn_clear = QPushButton("Limpar todas", panel)
        self._btn_clear.setProperty("variant", "chip")
        self._btn_clear.setProperty("size", "sm")
        self._btn_clear.setObjectName("TitlebarSettingsButton")
        self._btn_clear.clicked.connect(self._clear_all)
        actions_row.addWidget(self._btn_clear)
        header_wrap.addLayout(actions_row)

        pnl.addLayout(header_wrap)

        # Lista
        self._list = QListWidget(panel)
        self._list.setObjectName("NotificationList")
        self._list.setFrameShape(QFrame.NoFrame)
        # item do QListWidget transparente — o pill é o próprio _Row
        self._list.setStyleSheet("QListView{padding:0;margin:0;border:0;}")
        self._list.setContentsMargins(12, 6, 12, 6)
        self._list.setSelectionMode(QListWidget.NoSelection)
        self._list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._list.setSpacing(8)  # gap entre cards
        self._list.setWrapping(False)
        self._list.setResizeMode(QListView.Adjust)
        pnl.addWidget(self._list)

        # Fechar painel clicando em área vazia da lista
        self._list.viewport().installEventFilter(self)
        # Fechar clicando em qualquer lugar da página (fora do painel)
        self.installEventFilter(self)

        # ----- SIDEBAR (push) -----
        self._side = PushSidePanel(width=520, duration_ms=200, position="right", resizable=True)
        self._detail = _DetailPanel(self._side)
        self._side.setWidget(self._detail)
        rootH.addWidget(self._side)

        # Sempre que a largura do painel mudar, recalcule as linhas
        self._side.widthChanged.connect(lambda _w: self._recalc_all_rows())
        self._side.expandedChanged.connect(lambda _on: QTimer.singleShot(0, self._recalc_all_rows))

        # Carrega persistidos
        self._load_persisted()

        # Barramento
        bus = notification_bus()
        bus.addEntry.connect(self._on_add)
        bus.updateEntry.connect(self._on_update)
        bus.finishEntry.connect(self._on_finish)
        bus.removeEntry.connect(self._on_remove)

        # Interações
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.installEventFilter(self)  # recalcula em resize/layout

        # Emite contagem inicial
        self._emit_count()

    # ============== Event filter ==============

    def eventFilter(self, obj, ev):
        # 1) fechar painel se clicar em área vazia da lista
        if obj is self._list.viewport() and ev.type() == QEvent.MouseButtonPress:
            pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
            if self._list.itemAt(pos) is None and self._side.isExpanded():
                self._side.close()
                return True

        # 1b) clique em qualquer parte visual do item => abre detalhe
        if obj is self._list.viewport() and ev.type() == QEvent.MouseButtonRelease:
            pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
            it = self._list.itemAt(pos)
            if it is not None:
                self._on_item_clicked(it)
                return True

        # 2) Recalcular sizeHint das linhas quando a lista é redimensionada
        if obj is self._list and ev.type() in (QEvent.Resize, QEvent.LayoutRequest):
            self._recalc_all_rows()

        # 3) Clicar fora do painel fecha o painel
        if obj is self and hasattr(ev, "type") and ev.type() == QEvent.MouseButtonPress and self._side.isExpanded():
            self._side.close()
            return True

        return super().eventFilter(obj, ev)

    # ------------------ Persistência ------------------

    def _resolve_storage_path(self):
        try:
            win = self.window()
            settings = getattr(win, "settings", None)
            if settings and getattr(settings, "path", None):
                spath = Path(settings.path)
                app_root = None
                for cand in [spath] + list(spath.parents):
                    if cand.name == "app":
                        app_root = cand
                        break
                base = spath.parent if app_root is None else app_root
                cache_dir = (base / "assets" / "cache").resolve()
                cache_dir.mkdir(parents=True, exist_ok=True)
                return cache_dir / "_ui_notifications.json"
        except Exception:
            pass
        cache_dir = (Path.cwd() / "app" / "assets" / "cache").resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "_ui_notifications.json"

    def _save_persisted(self):
        try:
            payload = list(self._entries.values())
            self._storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print("[WARN] NotificationCenter: falha ao salvar:", e)

    def _load_persisted(self):
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for entry in data:
                        if not isinstance(entry, dict):
                            continue
                        _id = str(entry.get("id") or "")
                        if not _id:
                            continue
                        entry.setdefault("_ts_str", datetime.now().strftime("%H:%M:%S"))
                        entry.setdefault("persist", False)
                        entry.setdefault("expires_on_finish", True)
                        entry.setdefault("finished", False)
                        self._entries[_id] = entry
                        it = QListWidgetItem(self._list)
                        it.setData(Qt.UserRole, _id)
                        row = _Row(entry, self._list)
                        row.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                        row.sizeChanged.connect(lambda _=False, i=it, r=row: i.setSizeHint(r.sizeHint()))
                        it.setSizeHint(row.sizeHint())
                        self._list.addItem(it)
                        self._list.setItemWidget(it, row)
                        self._items[_id] = it
        except Exception as e:
            print("[WARN] NotificationCenter: falha ao carregar:", e)

    # ------------------ Barramento ------------------

    def _on_add(self, entry: dict):
        try:
            entry = dict(entry or {})
            _id = str(entry.get("id") or "")
            if not _id:
                return

            entry.setdefault("_ts_str", datetime.now().strftime("%H:%M:%S"))
            entry.setdefault("persist", False)
            entry.setdefault("expires_on_finish", True)
            entry.setdefault("finished", False)

            self._entries[_id] = entry

            if _id in self._items:
                w = self._list.itemWidget(self._items[_id])
                if isinstance(w, _Row):
                    w.update_from(entry)
                self._save_persisted()
                self._emit_count()
                if self._detail.current_id() == _id:
                    self._detail.set_entry(entry)
                return

            it = QListWidgetItem(self._list)
            it.setData(Qt.UserRole, _id)
            row = _Row(entry, self._list)
            row.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            row.sizeChanged.connect(lambda _=False, i=it, r=row: i.setSizeHint(r.sizeHint()))
            it.setSizeHint(row.sizeHint())
            self._list.addItem(it)
            self._list.setItemWidget(it, row)
            self._items[_id] = it

            self._save_persisted()
            self._emit_count()
        except Exception as e:
            print("[WARN] NotificationCenter._on_add:", e)

    def _on_update(self, patch: dict):
        try:
            _id = str(patch.get("id") or "")
            if not _id or _id not in self._entries:
                return
            self._entries[_id].update(patch)
            it = self._items.get(_id)
            if it:
                w = self._list.itemWidget(it)
                if isinstance(w, _Row):
                    w.update_from(self._entries[_id])
                    it.setSizeHint(w.sizeHint())
            self._save_persisted()
            self._emit_count()

            if self._detail.current_id() == _id:
                self._detail.set_entry(self._entries[_id])
                self._side.setTitle(self._entries[_id].get("title") or "Detalhes")
        except Exception as e:
            print("[WARN] NotificationCenter._on_update:", e)

    def _on_finish(self, _id: str):
        try:
            _id = str(_id or "")
            self._remove_ui(_id)
            if self._detail.current_id() == _id:
                self._detail.set_entry(None)
                self._side.close()
            self._save_persisted()
            self._emit_count()
        except Exception as e:
            print("[WARN] NotificationCenter._on_finish:", e)

    def _on_remove(self, _id: str):
        try:
            if _id == "__all__":
                self._remove_all_ui()
                self._save_persisted()
                self._emit_count()
                self._detail.set_entry(None)
                self._side.close()
                return

            _id = str(_id)
            self._remove_ui(_id)
            self._save_persisted()
            self._emit_count()

            if self._detail.current_id() == _id:
                self._detail.set_entry(None)
                self._side.close()
        except Exception as e:
            print("[WARN] NotificationCenter._on_remove:", e)

    # ------------------ Util ------------------

    def _on_item_clicked(self, it: QListWidgetItem):
        _id = it.data(Qt.UserRole)
        if not _id:
            return
        if self._detail.current_id() == _id and self._side.isExpanded():
            self._side.close()
            return
        entry = self._entries.get(str(_id))
        self._detail.set_entry(entry)
        self._side.setTitle((entry or {}).get("title") or "Detalhes")
        self._side.open()
        # garantir que o layout recalcula depois da animação
        QTimer.singleShot(0, self._recalc_all_rows)

    def _remove_ui(self, _id: str):
        self._entries.pop(_id, None)
        it = self._items.pop(_id, None)
        if it is not None:
            row = self._list.row(it)
            self._list.takeItem(row)

    def _remove_all_ui(self):
        self._entries.clear()
        self._items.clear()
        self._list.clear()

    def _clear_all(self):
        """Remove TODAS as notificações (pendentes, concluídas, persistentes, etc.)."""
        self._remove_all_ui()
        self._save_persisted()
        self._emit_count()
        self._detail.set_entry(None)
        self._side.close()

    def clear_finished_public(self):
        self._clear_all()

    def _emit_count(self):
        pending = sum(1 for e in self._entries.values() if not bool(e.get("finished", False)))
        self.countChanged.emit(int(pending))

    def _recalc_all_rows(self):
        for _id, it in list(self._items.items()):
            w = self._list.itemWidget(it)
            if isinstance(w, _Row):
                w._sync_heights()
                it.setSizeHint(w.sizeHint())
        self._list.updateGeometry()
        self._list.viewport().update()


def build(*_args, **_kwargs) -> QWidget:
    return NotificationCenter()
