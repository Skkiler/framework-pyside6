# ui/pages/theme_editor.py

from __future__ import annotations
from typing import Dict, Optional, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QColorDialog,
    QLabel, QFrame, QGridLayout, QLineEdit, QListWidget, QScrollArea,
    QSizePolicy
)
from PySide6.QtGui import QColor

from ui.core.frameless_window import FramelessDialog
from ui.widgets.titlebar import TitleBar

from ui.services.qss_renderer import load_base_qss, render_qss_from_base
import app.settings as cfg

# === Tokens padrão ===
DEFAULT_VARS: Dict[str, str] = {
    "bg_start": "#2f2f2f",
    "bg_end": "#3f3f3f",
    "bg": "#2f2f2f",
    "surface": "#383838",
    "text": "#e5e5e5",
    "text_hover": "#ffffff",
    "btn": "#3f7ad1",
    "btn_hover": "#347de9",
    "btn_text": "#ffffff",
    "hover": "#347de9",
    "accent": "#347de9",
    "input_bg": "#141111",
    "box_border": "#666666",
    "checkbox": "#e11717",
    "slider": "#e11717",
    "cond_selected": "#505050",
    "window_bg": "#2f2f2f",
}

GROUPS: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    ("Fundo", (
        ("Gradiente início", "bg_start"),
        ("Gradiente fim", "bg_end"),
        ("Plano de fundo", "bg"),
        ("Superfície (cards/menus)", "surface"),
    )),
    ("Texto", (
        ("Texto", "text"),
        ("Texto (hover)", "text_hover"),
    )),
    ("Botões / Acento", (
        ("Botão", "btn"),
        ("Botão (hover)", "btn_hover"),
        ("Texto do botão", "btn_text"),
        ("Cor de foco/hover global", "hover"),
        ("Acento (seleções/destaques)", "accent"),
    )),
    ("Entradas", (
        ("Fundo de entradas", "input_bg"),
        ("Bordas/contorno", "box_border"),
    )),
    ("Controles", (
        ("Checkbox / Radio", "checkbox"),
        ("Slider (barra)", "slider"),
    )),
    ("Seleção", (
        ("Linha/Item selecionado", "cond_selected"),
    )),
    ("Compat (opcional)", (
        ("window_bg", "window_bg"),
    )),
)

def _darken_hex(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
    clamp = lambda x: max(0, min(255, int(round(x*factor))))
    return f"#{clamp(r):02X}{clamp(g):02X}{clamp(b):02X}"

def _scope_qss(qss: str, scope_id: str = "ThemePreview") -> str:
    """Prefixa cada seletor com #ThemePreview para isolar o estilo no preview."""
    out = []
    for line in qss.splitlines():
        s = line.strip()
        if s.startswith(("/*","@")) or "{" not in line:
            out.append(line); continue
        left, right = line.split("{", 1)
        out.append(f"#{scope_id} {left.strip()}{{{right}")
    return "\n".join(out)


class SwatchButton(QPushButton):
    """Amostra de cor em formato CÍRCULO; clique abre QColorDialog."""
    def __init__(self, key: str, color_hex: str, on_pick, parent=None):
        super().__init__(parent)
        self.key = key; self._on_pick = on_pick
        self._size = 18  # diâmetro
        self.setFixedSize(self._size, self._size)
        self.setCursor(Qt.PointingHandCursor)
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Fixed); sp.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sp)
        self._apply(color_hex)
        self.clicked.connect(self._choose)

    def _apply(self, color_hex: str):
        radius = int(self._size/2)
        self.setStyleSheet(
            f"QPushButton{{background:{color_hex};"
            f"border:1px solid rgba(0,0,0,.35);border-radius:{radius}px;}}"
        )
        self.setToolTip(f"{self.key}: {color_hex}")

    def _choose(self):
        initial = QColor(self.toolTip().split(":")[-1].strip())
        col = QColorDialog.getColor(initial, self, f"Escolher cor para {self.key}")
        if col.isValid():
            self._on_pick(self.key, col.name()); self._apply(col.name())


# ========================= D I A L O G =========================
class ThemeEditorDialog(FramelessDialog):
    def __init__(self, name: str, props: Optional[Dict[str, str] | Dict[str, Dict[str, str]]], parent=None):
        super().__init__(parent)
        self.set_center_mode("window")
        self.theme_name = name

        incoming = {}
        if isinstance(props, dict):
            incoming = props.get("vars", props)
        incoming = {k: v for k, v in incoming.items() if isinstance(v, str) and v.startswith("#")}
        self.vars: Dict[str, str] = {**DEFAULT_VARS, **incoming}

        root = QWidget(self)
        v = QVBoxLayout(root); v.setContentsMargins(12,12,12,12); v.setSpacing(10)

        tb = TitleBar(f"Editar Tema: {name}", root)
        self.connect_titlebar(tb); v.addWidget(tb)
        v.addWidget(self._build_body(root), 1)

        actions = QHBoxLayout(); actions.addStretch(1)
        btn_reset = QPushButton("Restaurar padrão"); btn_reset.clicked.connect(self._reset_defaults)
        btn_ok = QPushButton("Salvar"); btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar"); btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_reset); actions.addWidget(btn_ok); actions.addWidget(btn_cancel)
        v.addLayout(actions)

        self.setCentralWidget(root)

        # ===== PERF: cache e debounce =====
        self._base_qss = load_base_qss(str(cfg.BASE_QSS))
        self._last_qss_applied: str = ""

        self._qssUpdateTimer = QTimer(self)
        self._qssUpdateTimer.setSingleShot(True)
        self._qssUpdateTimer.timeout.connect(self._apply_preview_qss)

        self._chrome_tokens = self._derive_tokens()
        self._apply_editor_chrome(self._chrome_tokens)

        self._apply_preview_qss()

        self.resize(980, 680)
        QTimer.singleShot(0, self._center_over_parent)

    def _build_body(self, parent: QWidget) -> QWidget:
        w = QWidget(parent)
        row = QHBoxLayout(w); row.setSpacing(12); row.setContentsMargins(0,0,0,0)

        # === Esquerda: WRAP com contorno + Scroll ===
        left_wrap = QFrame(w)
        left_wrap.setObjectName("EditorPane")           # frame com contorno
        left_wrap_l = QVBoxLayout(left_wrap)
        left_wrap_l.setContentsMargins(10, 10, 10, 10)  # igual à preview
        left_wrap_l.setSpacing(0)

        left_scroll = QScrollArea(left_wrap)
        left_scroll.setObjectName("EditorScroll")
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.viewport().setAutoFillBackground(False)
        left_wrap_l.addWidget(left_scroll)

        left = QWidget(); left.setObjectName("EditorLeft")
        left_scroll.setWidget(left)

        left_l = QVBoxLayout(left); left_l.setContentsMargins(0,0,0,0); left_l.setSpacing(6)

        for group_title, items in GROUPS:
            box = QFrame(left); box.setObjectName("groupBox")
            gl = QGridLayout(box)
            gl.setContentsMargins(8,6,8,6); gl.setHorizontalSpacing(6); gl.setVerticalSpacing(4)

            title_lbl = QLabel(group_title)
            f = title_lbl.font(); f.setPointSizeF(max(9.0, f.pointSizeF()-1)); title_lbl.setFont(f)
            gl.addWidget(title_lbl, 0, 0, 1, 2)

            r = 1
            for label, key in items:
                lbl = QLabel(label + ":")
                lf = lbl.font(); lf.setPointSizeF(max(9.0, lf.pointSizeF()-1)); lbl.setFont(lf)
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                gl.addWidget(lbl, r, 0)

                sw = SwatchButton(key, self.vars.get(key, DEFAULT_VARS[key]), self._on_pick, box)
                gl.addWidget(sw, r, 1, alignment=Qt.AlignRight | Qt.AlignVCenter)
                r += 1

            left_l.addWidget(box)
        left_l.addStretch(1)

        # refs para estilizar com tokens
        self._left_wrap = left_wrap
        self._left_scroll = left_scroll
        self._left_root = left

        # === Preview (maior): 1:2 ≈ 33/66 ===
        row.addWidget(left_wrap, 0)

        # pv_wrap (contorno da área de preview)
        pv_wrap = QFrame(w); pv_wrap.setObjectName("pvWrap")
        row.addWidget(pv_wrap, 1)
        row.setStretch(0, 1)
        row.setStretch(1, 2)

        pvw = QVBoxLayout(pv_wrap); pvw.setContentsMargins(12,10,12,12); pvw.setSpacing(6)
        t = QLabel("Pré-visualização"); t.setObjectName("pvWrapTitle")
        pvw.addWidget(t, 0, Qt.AlignLeft)

        # Raiz de escopo do preview
        self.preview_root = QWidget(pv_wrap); self.preview_root.setObjectName("ThemePreview")
        pvw.addWidget(self.preview_root, 1)
        scope_l = QVBoxLayout(self.preview_root); scope_l.setContentsMargins(0,0,0,0); scope_l.setSpacing(0)

        # Estrutura EXATA esperada pelo base.qss:
        # #FramelessFrame -> #FramelessContent
        frame = QFrame(self.preview_root); frame.setObjectName("FramelessFrame")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scope_l.addWidget(frame, 1)

        frame_l = QVBoxLayout(frame); frame_l.setContentsMargins(1, 1, 1, 1); frame_l.setSpacing(0)
        content = QWidget(frame); content.setObjectName("FramelessContent")
        frame_l.addWidget(content, 1)

        # Dentro do conteúdo: sidebar + content (como seu app)
        pl = QHBoxLayout(content); pl.setContentsMargins(0,0,0,0); pl.setSpacing(0)

        side = QFrame(content); side.setObjectName("pvSide"); side.setFixedWidth(180)
        sl = QVBoxLayout(side); sl.setContentsMargins(10,10,10,10); sl.setSpacing(6)
        st = QLabel("Menu"); st.setObjectName("pvSideTitle")
        lst = QListWidget(side); lst.addItems(["Início", "Relatórios", "Configurações"])
        sl.addWidget(st); sl.addWidget(lst, 1)

        main = QFrame(content); main.setObjectName("pvContent")
        cl = QVBoxLayout(main); cl.setContentsMargins(12,12,12,12); cl.setSpacing(8)
        title = QLabel("Pré-visualização"); title.setObjectName("pvTitle")
        card = QFrame(main); card.setObjectName("OuterPanel")
        card_l = QVBoxLayout(card); card_l.setContentsMargins(12,12,12,12); card_l.setSpacing(8)
        row2 = QHBoxLayout(); row2.setSpacing(8)
        inp = QLineEdit(card); inp.setPlaceholderText("Exemplo de input…")
        btn1 = QPushButton("Ação"); btn2 = QPushButton("Primário"); btn2.setProperty("variant", "primary")
        row2.addWidget(inp, 1); row2.addWidget(btn1); row2.addWidget(btn2)
        card_l.addLayout(row2)
        cl.addWidget(title); cl.addWidget(card, 1)

        pl.addWidget(side); pl.addWidget(main, 1)
        return w

    # ---- tokens ----
    def _derive_tokens(self) -> Dict[str, str]:

        t = dict(self.vars)

        # 1) Derivar gradiente do 'bg' se o usuário NÃO personalizou bg_start/bg_end
        bg = t.get("bg", DEFAULT_VARS["bg"])
        user_kept_defaults = (
            t.get("bg_start", DEFAULT_VARS["bg_start"]) == DEFAULT_VARS["bg_start"]
            and t.get("bg_end",   DEFAULT_VARS["bg_end"])   == DEFAULT_VARS["bg_end"]
        )
        if user_kept_defaults:
            t["bg_start"] = _darken_hex(bg, 0.95)
            t["bg_end"]   = _darken_hex(bg, 0.80)

        # 2) content_bg: usado em painéis / TopBar
        t["content_bg"] = t.get("surface", DEFAULT_VARS["surface"])

        # 3) loading_overlay_bg translúcido a partir do accent (fallbacks)
        def _rgba(hex_color: str, alpha: float) -> str:
            h = hex_color.lstrip("#")
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
            a = max(0.0, min(1.0, alpha))
            return f"rgba({r},{g},{b},{a:.3f})"

        base_for_overlay = t.get("accent") or t.get("slider") or DEFAULT_VARS["accent"]
        t["loading_overlay_bg"] = _rgba(base_for_overlay, 0.25)

        return t

    # Estiliza o painel esquerdo (fora do preview) com surface/text/slider/box_border
    def _apply_editor_chrome(self, tokens: Dict[str, str]):
        if not all(hasattr(self, x) for x in ("_left_root", "_left_scroll", "_left_wrap")):
            return
        surface = tokens.get("surface", "#383838")
        text = tokens.get("text", "#e5e5e5")
        slider = tokens.get("slider", "#e11717")
        border = tokens.get("box_border", "#666666")

        # Contorno e fundo do painel
        self._left_wrap.setStyleSheet(
            f"""
            QFrame#EditorPane {{
                background: {surface};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            """
        )

        # Fundo do conteúdo = surface; filhos transparentes herdam o fundo
        self._left_root.setStyleSheet(
            f"""
            QWidget#EditorLeft {{
                background: {surface};
                color: {text};
            }}
            QWidget#EditorLeft * {{
                color: {text};
                background: transparent;
            }}
            QFrame#groupBox {{
                background: transparent;
                border: none;
            }}
            """
        )

        # Scrollbar fina + transparências no scroll/viewport
        self._left_scroll.setStyleSheet(
            f"""
            QScrollArea#EditorScroll {{
                background: transparent;
            }}
            QScrollArea#EditorScroll > QWidget {{
                background: transparent;
            }}
            QScrollArea#EditorScroll > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                width: 6px;
                margin: 0;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                min-height: 20px;
                border-radius: 3px;
                background: {slider};
                border: 1px solid {border};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            """
        )

    # ---- aplica QSS na preview com cache/compare ----
    def _apply_preview_qss(self):
        tokens = self._derive_tokens()

        base_rendered = render_qss_from_base(self._base_qss, tokens)
        scoped_qss = _scope_qss(base_rendered, "ThemePreview")
        scoped_qss += (
            f"\n#ThemePreview QFrame#OuterPanel "
            f"{{ background: {tokens.get('surface', DEFAULT_VARS['surface'])}; }}"
        )

        if scoped_qss == self._last_qss_applied:
            return

        self.preview_root.setUpdatesEnabled(False)
        try:
            st = self.preview_root.style()
            st.unpolish(self.preview_root)
            self.preview_root.setStyleSheet(scoped_qss)
            st.polish(self.preview_root)
            self._last_qss_applied = scoped_qss
        finally:
            self.preview_root.setUpdatesEnabled(True)
            self.preview_root.update()

    # debounce ~60 fps
    def _schedule_qss_update(self, delay_ms: int = 16):
        if self._qssUpdateTimer.isActive():
            self._qssUpdateTimer.stop()
        self._qssUpdateTimer.start(delay_ms)

    # slots
    def _reset_defaults(self):
        self.vars = dict(DEFAULT_VARS)
        self._schedule_qss_update()

    def _on_pick(self, key: str, color_hex: str):
        self.vars[key] = color_hex
        self._schedule_qss_update()

    # API pública
    def get_theme_data(self) -> Dict[str, Dict[str, str]]:
        out = dict(DEFAULT_VARS)
        out.update({k: v for k, v in self.vars.items() if isinstance(v, str) and v.startswith("#")})
        return {"vars": out}

    @property
    def props(self) -> Dict[str, str]:
        out = dict(DEFAULT_VARS)
        out.update({k: v for k, v in self.vars.items() if isinstance(v, str) and v.startswith("#")})
        return out
