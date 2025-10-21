# ui/widgets/topbar.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from ui.widgets.buttons import Controls


class TopBar(QWidget):

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

        # Título opcional
        self.title_label = QLabel(self)
        self.title_label.setObjectName("TopBarTitle")
        layout.addWidget(self.title_label)

        # Espaçador (empurra conteúdo para a esquerda)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Inicializa o título
        self.set_title(title)

    # =====================================================
    # Métodos públicos
    # =====================================================

    def set_title(self, text: str | None):
        """Define o texto da TopBar ou oculta o label se None/vazio."""
        if text and text.strip():
            self.title_label.setText(text.strip())
            self.title_label.setVisible(True)
        else:
            self.title_label.clear()
            self.title_label.setVisible(False)

    def title(self) -> str:
        """Retorna o texto atual do título."""
        return self.title_label.text()
