from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QStackedLayout, QVBoxLayout, QHBoxLayout,  QLabel
)
from PyQt6.QtCore import Qt

from sieve_analysis import SA_Screen as SA
from products_customers import PC_Screen as PC
from assemble_grain_curve import AGC_Screen as AGC

from local_data import load_data

# TODO: General cleanup:
#       - remove the use of block_sql stuff and use the signal block - as much as possible.
#       - make all the things that use tables save the currently selected id so we dont check the table always - or maybe not..?

# TODO: There are likely many optimizations doable on the sql-setup side; like why should all the batch iids contain the production_area? (makes it work dumb too)

# i likely want a clear button too - for all sub-widgets/layouts.
# and probably to make every sub-widget/layout a class too, lol.

# i have to add exceptions to a lot of shit - and maby make them display with message boxes..?

class HomeScreen(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        welcome_label = QLabel("Welcome to the App!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(welcome_label)

        button_h_layout = QHBoxLayout()
        button_h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_add = QPushButton("P03 resultater")
        btn_add.setFixedSize(150, 40)
        btn_add.clicked.connect(lambda: self.main_window.set_index(1))
        button_h_layout.addWidget(btn_add)

        btn_insert = QPushButton("Produkter og kunder")
        btn_insert.setFixedSize(150, 40)
        btn_insert.clicked.connect(lambda: self.main_window.set_index(2))
        button_h_layout.addWidget(btn_insert)

        btn_search = QPushButton("Sammensæt kurver")
        btn_search.setFixedSize(150, 40)
        btn_search.clicked.connect(lambda: self.main_window.set_index(3))
        button_h_layout.addWidget(btn_search)

        layout.addLayout(button_h_layout)
        
import matplotlib.pyplot as plt
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App (PyQt6)")
        # self.setFixedSize(QSize(900, 720))
        self.resize(900, 720)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        self.stacked_layout = QStackedLayout()

        def newReturnArea():
            hlayout = QHBoxLayout()
            return_button = QPushButton("Retur menu")
            return_button.setStyleSheet("color: red;")
            return_button.clicked.connect(lambda: self.set_index(0))
            hlayout.addWidget(return_button)

            reload_button = QPushButton("🔄")
            reload_button.setFixedSize(30, 30)
            # reload_button.setFixedSize(24, 24)
            reload_button.clicked.connect(lambda: load_data())
            hlayout.addWidget(reload_button)
            return hlayout

        self.stacked_layout.addWidget(HomeScreen(self))
        self.stacked_layout.addWidget(SA(self, newReturnArea))
        self.PC = PC(self, newReturnArea)
        self.stacked_layout.addWidget(self.PC)
        self.stacked_layout.addWidget(AGC(self, newReturnArea))

        stacked_widget_container = QWidget()
        stacked_widget_container.setLayout(self.stacked_layout)
        main_layout.addWidget(stacked_widget_container)
        
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        self.set_index(0)
        
    def closeEvent(self, event):
        plt.close('all')
        event.accept()

    def goToProduct(self, id):
        table = self.PC.P.table_widget

        matching_items = table.findItems(id, Qt.MatchFlag.MatchExactly)
        if matching_items:
            item = matching_items[0]
            row_index = item.row()
            table.clearSelection()
            table.selectRow(row_index)

        self.stacked_layout.setCurrentIndex(2)
        
    def set_index(self, idx):
        self.stacked_layout.setCurrentIndex(idx)
        if (idx == 0):
            self.setWindowTitle("App")
        #else:
        #    self.stacked_layout.currentWidget().open()

if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    window = MainWindow()
    window.show()
    app.exec()

    # print(QInputDialog.getText(None, "Gem om nyt produkt", "Nyt id"))