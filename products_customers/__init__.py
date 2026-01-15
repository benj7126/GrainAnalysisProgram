from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)

from .products import P_Screen as P
from .customers import C_Screen as C

class PC_Screen(QWidget):
    def __init__(self, main_window_ref, newReturnArea, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref

        self.P = P(self.main_window)
        self.C = C(self.main_window)

        self.init_ui(newReturnArea)

    def init_ui(self, newReturnArea):
        main_layout = QVBoxLayout()
        tab_widget = QTabWidget()
        tab_widget.addTab(self.P, "Produkter")
        tab_widget.addTab(self.C, "Kunder")

        main_layout.addWidget(tab_widget)

        main_layout.addLayout(newReturnArea())

        self.updateGeometry()
        self.adjustSize()

        self.setLayout(main_layout)