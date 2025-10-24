# ui/widgets/topbar.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy, QMenu, QToolButton
from PySide6.QtCore import Qt, Signal
from ui.widgets.buttons import Controls


class TopBar(QWidget):
    """TopBar com breadcrumb clicável (à esquerda, após o hambúrguer) e título opcional + sino com badge."""

    breadcrumbClicked = Signal(str)
    openNotificationsRequested = Signal()
    clearNotificationsRequested = Signal()
    setUnreadCountRequested = Signal(int)

    def __init__(self, onHamburgerClick=None, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Botão de menu (hambúrguer)
        self.hamburger = Controls.IconButton("☰", self, tooltip="Menu")
        if onHamburgerClick:
            self.hamburger.clicked.connect(onHamburgerClick)
        layout.addWidget(self.hamburger)

        # ---- Breadcrumb (texto clicável) logo após o hambúrguer ----
        self._breadcrumb_container = QWidget(self)
        self._breadcrumb_container.setObjectName("TopBarBreadcrumbContainer")
        self._bc_layout = QHBoxLayout(self._breadcrumb_container)
        self._bc_layout.setContentsMargins(0, 0, 0, 0)
        self._bc_layout.setSpacing(6)
        self._breadcrumb_container.setVisible(False)
        layout.addWidget(self._breadcrumb_container)

        # Título (fica depois do breadcrumb)
        self.title_label = QLabel(self)
        self.title_label.setObjectName("TopBarTitle")
        layout.addWidget(self.title_label)

        # Espaçador (empurra extra para a direita)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # ===== Botão de notificações (QToolButton pintável) =====
        self.btn_more = QToolButton(self)
        self.btn_more.setObjectName("TitleBarButton")
        self.btn_more.setText("✉")
        self.btn_more.setToolTip("Notificações")
        self.btn_more.setAutoRaise(True)
        self.btn_more.setCursor(Qt.PointingHandCursor)
        self.btn_more.setFixedSize(32, 24)
        f = self.btn_more.font()
        f.setFamily("Segoe UI Symbol")
        self.btn_more.setFont(f)
        self.btn_more.setPopupMode(QToolButton.InstantPopup)
        self.btn_more.clicked.connect(self.openNotificationsRequested.emit)

        # Badge de não lidas
        self._badge = QLabel("0", self)
        self._badge.setObjectName("BellBadge")     # usa estilos do QSS (#BellBadge)
        self._badge.setVisible(False)

        layout.addWidget(self.btn_more, 0, Qt.AlignRight)
        layout.addWidget(self._badge, 0, Qt.AlignRight)

        # Permite que alguém externo ajuste o badge
        self.setUnreadCountRequested.connect(self._onUnreadChanged)

        # Inicializa o título
        self.set_title(title)

    # =====================================================
    # Métodos públicos
    # =====================================================

    def set_title(self, text: str | None):
        """Define o texto da TopBar ou oculta o label se None/vazio."""
        if text and text.strip():
            self.title_label.setText(text.strip())
            # Visibilidade do título é controlada também pelo breadcrumb (para evitar duplicação).
            # Só mostramos aqui se o breadcrumb estiver oculto.
            if not self._breadcrumb_container.isVisible():
                self.title_label.setVisible(True)
        else:
            self.title_label.clear()
            self.title_label.setVisible(False)

    def title(self) -> str:
        """Retorna o texto atual do título."""
        return self.title_label.text()

    def set_breadcrumb(self, parts: list[tuple[str, str]] | None):
        # Limpa o container atual
        while self._bc_layout.count():
            item = self._bc_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not parts:
            # Sem breadcrumb → mostra título se existir
            self._breadcrumb_container.setVisible(False)
            if self.title_label.text().strip():
                self.title_label.setVisible(True)
            return

        # Com breadcrumb → escondemos o título para não duplicar o último segmento
        self.title_label.setVisible(False)

        total = len(parts)
        for idx, (label, acc_path) in enumerate(parts):
            is_last = (idx == total - 1)

            if is_last:
                # Último item: apenas texto “current”
                curr = QLabel(label, self._breadcrumb_container)
                curr.setObjectName("BreadcrumbCurrent")
                curr.setProperty("current", True)
                curr.setAlignment(Qt.AlignVCenter)
                self._bc_layout.addWidget(curr)
            else:
                # Item clicável com cara de texto
                link = Controls.LinkLabel(label, self._breadcrumb_container)
                link.setObjectName("BreadcrumbLink")
                link.clicked.connect(lambda p=acc_path: self.breadcrumbClicked.emit(p))
                self._bc_layout.addWidget(link)

                # Separador
                sep = QLabel("/", self._breadcrumb_container)
                sep.setObjectName("BreadcrumbSeparator")
                sep.setAlignment(Qt.AlignVCenter)
                self._bc_layout.addWidget(sep)

        self._breadcrumb_container.setVisible(True)

    # ===== internos =====
    def _onUnreadChanged(self, n: int):
        try:
            n = max(0, int(n))
        except Exception:
            n = 0
        self._badge.setText(str(n))
        self._badge.setVisible(n > 0)
