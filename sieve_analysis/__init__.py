import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)

from .new_results import NR_Screen as NR
from .data import D_Screen as D

class SA_Screen(QWidget):
    def __init__(self, main_window_ref, newReturnArea, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref

        self.NR = NR(self.main_window)
        self.D = D(self.main_window)

        self.init_ui(newReturnArea)

    def init_ui(self, newReturnArea):
        main_layout = QVBoxLayout()
        tab_widget = QTabWidget()
        tab_widget.addTab(self.NR, "Nyt resultat")
        tab_widget.addTab(self.D, "Se gamle resultater")

        main_layout.addWidget(tab_widget)

        main_layout.addLayout(newReturnArea())

        self.updateGeometry()
        self.adjustSize()

        self.setLayout(main_layout)
