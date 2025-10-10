# ui/widgets/topbar.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from ..widgets.buttons import Controls

class TopBar(QWidget):
    def __init__(self, onHamburgerClick, title: str):
        super().__init__()
        self.setObjectName("TopBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        hamb = Controls.IconButton("☰", self, tooltip="Menu")
        hamb.clicked.connect(onHamburgerClick)

        self.title = QLabel(title)
        lay.addWidget(hamb)
        lay.addWidget(self.title)
        lay.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
