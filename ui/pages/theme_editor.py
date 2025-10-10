# ui/pages/theme_editor.py

from __future__ import annotations
from functools import partial
from typing import Dict, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QWidget, QColorDialog, QLabel, QFrame, QGridLayout, QLineEdit, QListWidget
)

# === MODELO PADRÃO (apenas VARS) ===
# Cobrem os tokens usados pelo base.qss (e nossos QSSs “ricos”)
DEFAULT_VARS: Dict[str, str] = {
    # Fundo
    "bg_start": "#2f2f2f",
    "bg_end":   "#3f3f3f",
    "bg":       "#2f2f2f",
    "surface":  "#383838",

    # Texto
    "text":       "#e5e5e5",
    "text_hover": "#ffffff",

    # Botões / Acento
    "btn":       "#3f7ad1",
    "btn_hover": "#347de9",
    "btn_text":  "#ffffff",
    "hover":     "#347de9",
    "accent":    "#347de9",   # usado em seleção, títulos, etc.

    # Inputs & Borda
    "input_bg":    "#141111",
    "box_border":  "#666666",

    # Controles
    "checkbox": "#e11717",
    "slider":   "#e11717",

    # Seleção
    "cond_selected": "#505050",

    # Paleta/compat
    "window_bg": "#2f2f2f",
}

# === GRUPOS (ordem & rótulos) ===
# Apenas campos de vars (o editor salva sempre { "vars": {...} })
GROUPS: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    ("Fundo", (
        ("Gradiente início", "bg_start"),
        ("Gradiente fim",    "bg_end"),
        ("Plano de fundo",   "bg"),
        ("Superfície (cards/menus)", "surface"),
    )),
    ("Texto", (
        ("Texto",        "text"),
        ("Texto (hover)","text_hover"),
    )),
    ("Botões / Acento", (
        ("Botão",         "btn"),
        ("Botão (hover)", "btn_hover"),
        ("Texto do botão","btn_text"),
        ("Cor de foco/hover global", "hover"),
        ("Acento (seleções/destaques)", "accent"),
    )),
    ("Entradas", (
        ("Fundo de entradas", "input_bg"),
        ("Bordas/contorno",   "box_border"),
    )),
    ("Controles", (
        ("Checkbox / Radio", "checkbox"),
        ("Slider (barra)",   "slider"),
    )),
    ("Seleção", (
        ("Linha/Item selecionado", "cond_selected"),
    )),
    ("Compat (opcional)", (
        ("window_bg", "window_bg"),
    )),
)

#-------------------------- Helpers ----------------------

def _clamp(x: float) -> int:
    return max(0, min(255, int(round(x))))

def _parse_hex(s: str) -> tuple[int, int, int, int]:
    s = s.strip()
    if not s.startswith("#"): return (47,47,47,255)
    s = s[1:]
    if len(s) == 3:
        r,g,b = (int(s[0]*2,16), int(s[1]*2,16), int(s[2]*2,16))
        return (r,g,b,255)
    if len(s) == 6:
        return (int(s[0:2],16), int(s[2:4],16), int(s[4:6],16), 255)
    if len(s) == 8:
        a = int(s[0:2],16)
        return (int(s[2:4],16), int(s[4:6],16), int(s[6:8],16), a)
    return (47,47,47,255)

def _darken_hex(hex_color: str, factor: float) -> str:
    """factor < 1.0 escurece (ex.: 0.8 = 20% mais escuro)"""
    r,g,b,a = _parse_hex(hex_color)
    r = _clamp(r*factor); g = _clamp(g*factor); b = _clamp(b*factor)
    return f"#{r:02X}{g:02X}{b:02X}" if a==255 else f"#{a:02X}{r:02X}{g:02X}{b:02X}"


#-------------------------- Editor ----------------------

class SwatchButton(QPushButton):
    """Botão pequeno com pré-visualização da cor + hex como tooltip."""
    def __init__(self, key: str, color_hex: str, on_pick, parent=None):
        super().__init__(parent)
        self.key = key
        self._on_pick = on_pick
        self.setFixedSize(40, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{key}: {color_hex}")
        self._apply_color(color_hex)
        self.clicked.connect(self._choose)

    def _apply_color(self, color_hex: str):
        self.setStyleSheet(
            "QPushButton {"
            f"background: {color_hex};"
            "border: 1px solid rgba(0,0,0,0.35);"
            "border-radius: 6px;"
            "}"
        )
        self.setToolTip(f"{self.key}: {color_hex}")

    def _choose(self):
        initial = QColor(self.toolTip().split(":")[-1].strip())
        col = QColorDialog.getColor(initial, self, f"Escolher cor para {self.key}")
        if col.isValid():
            self._on_pick(self.key, col.name())
            self._apply_color(col.name())


class ThemeEditorDialog(QDialog):

    def __init__(self, name: str, props: Optional[Dict[str, str] | Dict[str, Dict[str, str]]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Tema: {name}")
        self.setMinimumWidth(680)
        self.theme_name = name

        # Normaliza entrada: aceitar {"vars": {...}} ou dict simples de tokens
        incoming_vars = {}
        if isinstance(props, dict):
            if "vars" in props and isinstance(props["vars"], dict):
                incoming_vars = {k: v for k, v in props["vars"].items() if isinstance(v, str) and v.startswith("#")}
            else:
                incoming_vars = {k: v for k, v in props.items() if isinstance(v, str) and v.startswith("#")}

        self.vars: Dict[str, str] = dict(DEFAULT_VARS)
        self.vars.update(incoming_vars)  # prioridade para valores do tema

        self._swatches: Dict[str, SwatchButton] = {}

        self._build_ui()
        self._refresh_preview()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Cabeçalho
        header = QLabel("Ajuste as cores do tema. Clique nos quadradinhos para escolher as cores.")
        header.setStyleSheet("font-weight:600; margin-bottom:6px;")
        root.addWidget(header)

        # Conteúdo em 2 colunas: (esquerda = editores) | (direita = preview)
        row = QHBoxLayout()
        row.setSpacing(12)
        root.addLayout(row)

        # Esquerda: grupos com swatches
        left = QWidget(self)
        left_l = QVBoxLayout(left); left_l.setContentsMargins(0,0,0,0); left_l.setSpacing(8)

        for group_title, items in GROUPS:
            box = QFrame(left); box.setFrameShape(QFrame.StyledPanel); box.setObjectName("groupBox")
            gl = QGridLayout(box); gl.setContentsMargins(10,8,10,10); gl.setHorizontalSpacing(8); gl.setVerticalSpacing(6)

            title = QLabel(group_title); title.setStyleSheet("font-weight:600;")
            gl.addWidget(title, 0, 0, 1, 2)

            row_i = 1
            for label, key in items:
                lab = QLabel(label + ":")
                sw = SwatchButton(key, self.vars.get(key, DEFAULT_VARS.get(key, "#ffffff")), self._on_pick, box)
                self._swatches[key] = sw
                gl.addWidget(lab, row_i, 0)
                gl.addWidget(sw,  row_i, 1)
                row_i += 1

            left_l.addWidget(box)

        left_l.addStretch(1)
        row.addWidget(left, 0)

        # Direita: Preview dentro de um WRAP com título e borda grossa
        pv_wrap = QFrame(self)
        pv_wrap.setObjectName("pvWrap")
        pvw_l = QVBoxLayout(pv_wrap)
        pvw_l.setContentsMargins(12, 10, 12, 12)
        pvw_l.setSpacing(6)

        pv_title = QLabel("Pré-visualização")
        pv_title.setObjectName("pvWrapTitle")
        pvw_l.addWidget(pv_title, 0, Qt.AlignLeft)

        self.preview = self._build_preview_widget(pv_wrap)
        pvw_l.addWidget(self.preview, 1)

        row.addWidget(pv_wrap, 1)

        # Rodapé: ações
        actions = QHBoxLayout(); actions.addStretch(1)
        reset = QPushButton("Restaurar padrão"); reset.clicked.connect(self._reset_defaults)
        ok = QPushButton("Salvar"); ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancelar"); cancel.clicked.connect(self.reject)
        actions.addWidget(reset); actions.addWidget(ok); actions.addWidget(cancel)
        root.addLayout(actions)

        # Estilinho leve do editor (lado esquerdo)
        self.setStyleSheet("""
        QFrame#groupBox {
            background: rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.15);
            border-radius: 8px;
        }
        """)

    def _build_preview_widget(self, parent: QWidget) -> QWidget:

        w = QWidget(parent)
        w.setObjectName("previewRoot")
        lay = QHBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        # Sidebar fake
        side = QFrame(w); side.setObjectName("pvSide"); side.setFixedWidth(180)
        side_l = QVBoxLayout(side); side_l.setContentsMargins(10,10,10,10); side_l.setSpacing(6)
        side_title = QLabel("Menu"); side_title.setObjectName("pvSideTitle")
        lst = QListWidget(side); lst.addItems(["Início", "Relatórios", "Configurações"])
        side_l.addWidget(side_title); side_l.addWidget(lst, 1)

        # Conteúdo
        content = QFrame(w); content.setObjectName("pvContent")
        cl = QVBoxLayout(content); cl.setContentsMargins(12,12,12,12); cl.setSpacing(8)

        title = QLabel("Pré-visualização"); title.setObjectName("pvTitle")

        card = QFrame(content)
        card.setObjectName("OuterPanel")
        
        card_l = QVBoxLayout(card); card_l.setContentsMargins(12,12,12,12); card_l.setSpacing(8)

        # Input + Botões
        row = QHBoxLayout(); row.setSpacing(8)
        inp = QLineEdit(card); inp.setPlaceholderText("Exemplo de input…")
        btn_ok = QPushButton("Ação"); btn_cancel = QPushButton("Cancelar")
        row.addWidget(inp, 1); row.addWidget(btn_ok); row.addWidget(btn_cancel)

        card_l.addLayout(row)
        cl.addWidget(title); cl.addWidget(card, 1)

        lay.addWidget(side); lay.addWidget(content, 1)

        self._pv_refs = {
            "root": w, "side": side, "side_title": side_title, "list": lst,
            "content": content, "title": title, "card": card, "input": inp,
            "btn_ok": btn_ok, "btn_cancel": btn_cancel
        }
        return w

    # ---------- Ações ----------
    def _reset_defaults(self):
        self.vars = dict(DEFAULT_VARS)
        # atualiza swatches
        for k, sw in self._swatches.items():
            col = self.vars.get(k, DEFAULT_VARS.get(k, "#ffffff"))
            sw._apply_color(col)
        self._refresh_preview()

    def _on_pick(self, key: str, color_hex: str):
        self.vars[key] = color_hex
        self._refresh_preview()

    # ---------- Preview ----------
    def _refresh_preview(self):
        th = self.vars

        # Fundo do preview (gradiente)
        grad = (
            "qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            f"stop:0 {th.get('bg_start', DEFAULT_VARS['bg_start'])}, "
            f"stop:1 {th.get('bg_end',   DEFAULT_VARS['bg_end'])})"
        )

        # Mesmo derivado que o app usa: content_bg = bg_start 20% mais escuro
        bg0 = th.get('bg_start', DEFAULT_VARS['bg_start'])
        content_bg = _darken_hex(bg0, 0.8)

        qss = f"""
        /* ===== Moldura do preview ===== */
        QFrame#pvWrap {{
            background: transparent;
            border: 3px solid {th.get('box_border')};
            border-radius: 12px;
        }}
        QLabel#pvWrapTitle {{
            color: {th.get('text')};
            font-weight: 700;
            padding: 2px 10px;
            background: {th.get('surface')};
            border: 1px solid {th.get('box_border')};
            border-radius: 6px;
        }}

        /* ===== Área real do preview ===== */
        QWidget#previewRoot {{
            background: {grad};
            border: 1px solid {th.get('box_border')};
            border-radius: 10px;
        }}

        /* Sidebar dentro do preview como caixa externa sólida */
        QFrame#pvSide {{
            background: {content_bg};
            border-right: 1px solid {th.get('box_border')};
        }}
        QLabel#pvSideTitle {{
            color: {th.get('text')};
            font-weight: 600;
            margin-left: 2px;
        }}

        QListWidget {{
            background: {th.get('surface')};
            border: 1px solid {th.get('box_border')};
            border-radius: 6px;
            color: {th.get('text')};
        }}
        QListWidget::item {{ padding: 8px 10px; }}
        QListWidget::item:selected {{
            background: {th.get('accent')};
            color: {th.get('text')};
        }}

        QFrame#pvContent {{ background: transparent; }}
        QLabel#pvTitle   {{ color: {th.get('text')}; font-weight: 600; }}

        /* Card do conteúdo = caixa externa sólida */
        QFrame#pvCard, QFrame#OuterPanel {{
            background: {content_bg};
            border: 1px solid {th.get('box_border')};
            border-radius: 8px;
        }}

        QLineEdit {{
            background: {th.get('input_bg')};
            color: {th.get('text')};
            border: 1px solid {th.get('box_border')};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QPushButton {{
            background: {th.get('btn')};
            color: {th.get('btn_text')};
            border: none;
            border-radius: 7px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background: {th.get('btn_hover')};
            color: {th.get('btn_text')};
        }}
        """
        self.preview.setStyleSheet(qss)

    # ---------- API ----------
    def get_theme_data(self) -> Dict[str, Dict[str, str]]:
        """Retorna no padrão final esperado: {"vars": {...}}"""
        # Garante todas as chaves essenciais
        out = dict(DEFAULT_VARS)
        out.update({k: v for k, v in self.vars.items() if isinstance(v, str) and v.startswith("#")})
        return {"vars": out}

    # Compatibilidade com códigos antigos que esperavam dlg.props (apenas vars)
    @property
    def props(self) -> Dict[str, str]:
        out = dict(DEFAULT_VARS)
        out.update({k: v for k, v in self.vars.items() if isinstance(v, str) and v.startswith("#")})
        return out
