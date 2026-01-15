import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)

from .handle_recept import HR_Screen as HR
from .raw_sands import RS_Screen as RS

class AGC_Screen(QWidget):
    def __init__(self, main_window_ref, newReturnArea, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref

        self.HR = HR(self.main_window)
        self.RS = RS(self.main_window)

        self.init_ui(newReturnArea)

    def init_ui(self, newReturnArea):
        main_layout = QVBoxLayout()
        tab_widget = QTabWidget()
        tab_widget.addTab(self.HR, "Opret produkt")
        tab_widget.addTab(self.RS, "Råvarer")

        main_layout.addWidget(tab_widget)

        main_layout.addLayout(newReturnArea())

        self.updateGeometry()
        self.adjustSize()

        self.setLayout(main_layout)