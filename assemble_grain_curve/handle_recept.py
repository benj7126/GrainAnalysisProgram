import win32clipboard
import win32con
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QSizePolicy, QComboBox, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from local_data import sands, add_sand_event, add_sand_sieve_event, addReloadEvent, products
from sql import get_session, RawSandSieve
from generate_curve import createCurve
from excel_drop_label import ExcelDropLabel
from general_methods import inner_create_new_product_or_update, getUpperAndLower
import matplotlib.pyplot as plt

from general_methods import conv, stringify

from comma_dot_verify import CommaDotDoubleValidator

validator = CommaDotDoubleValidator()

def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                clear_layout(item.layout())

def get_sets():
    data = ""
    win32clipboard.OpenClipboard()
    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
        raw_data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
        try:
            data = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                data = raw_data.decode('cp1252')
            except UnicodeDecodeError:
                print("Could not decode clipboard data with utf-8 or cp1252.")
                return []
    win32clipboard.CloseClipboard()
    
    return [(parts[3].upper() if len(parts) > 3 else "", parts[7].replace(",", ".") if len(parts) > 6 else "") for line in data.splitlines() if (parts := line.split("\t"))]


class HR_Screen(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.rows = []
        self.sand_cache = {}
        self.init_ui()

        self.block_sql = False
        self.live_fig, self.live_ax = None, None
        self.block_reflect = False

        self.new_dialog = QInputDialog()
        self.new_dialog.setWindowTitle("Opret nyt produkt")
        self.new_dialog.setOkButtonText("Opret")
        self.new_dialog.setCancelButtonText("Annuler")
    
    def updateCurve(self, list):
        if self.live_fig and self.live_fig.number in plt.get_fignums():
            self.estimateCurve(list)

    
    def estimateCurve(self, list):
        if not self.live_fig or self.live_fig.number not in plt.get_fignums():
            self.live_fig, self.live_ax = None, None

        upper, lower = getUpperAndLower(list)            

        self.live_fig, self.live_ax = createCurve(list, upper, lower, self.live_fig, self.live_ax)

    def get_new_product_id(self):
        self.new_dialog.setLabelText(f'Angiv produkt ID for dette produkt:')
        while True:
            if self.new_dialog.exec():
                text = self.new_dialog.textValue()

                if text.strip() == "":
                    QMessageBox.warning(None, "Ugyldigt Input", "Der skal angives et ID.\nPrøv venligst igen.")
                elif text in products:
                    QMessageBox.warning(None, "Ugyldigt Input", f"'{text}' findes allerede. Angiv venligst et anden ID.")
                else:
                    return text
            else:
                return False
    
    def create_new_product(self, list):
        id = self.get_new_product_id()

        if id:
            rows = [[row[0].currentText(), row[1].currentText(), row[2].text()] for row in self.rows[:-1]] # ignore the last empty row
            inner_create_new_product_or_update(list, id, rows)

            for i in range(10):
                self.sieve_items[i].setText("")
        
            ## TODO: should try to make a single method for aksing these popups?
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Følg produkt.")
            msg_box.setText("Gå til det oprettede produkt?")

            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            response = msg_box.exec()

            self.clear_rows()
            if response == QMessageBox.StandardButton.Yes:
                self.main_window.goToProduct(id)
            
    def getRow(self):
        layout = QHBoxLayout()

        article_number = QComboBox()
        article_number.setFixedSize(85, 24)
        article_number.setEditable(True)
        article_number.addItems(sorted(sands.keys()))
        article_number.setCurrentIndex(-1)
        article_number.lineEdit().setPlaceholderText("Varenr.")

        layout.addWidget(article_number)

        product_designation = QComboBox()
        product_designation.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        product_designation.setFixedHeight(24)
        product_designation.setEditable(True)
        product_designation.addItems([sands[key] for key in sorted(sands.keys())])
        product_designation.setCurrentIndex(-1)
        product_designation.lineEdit().setPlaceholderText("Vare betegnelse")

        layout.addWidget(product_designation)

        def article_number_changed():
            product_designation.setCurrentIndex(article_number.currentIndex())

        def new_row():
            article_number.currentIndexChanged.disconnect(new_row)
            article_number.currentIndexChanged.connect(article_number_changed)
            self.inner_layout.addLayout(self.getRow())
            product_designation.setCurrentIndex(article_number.currentIndex())
    

        article_number.currentIndexChanged.connect(new_row)

        def product_designation_changed():
            article_number.setCurrentIndex(product_designation.currentIndex())

        product_designation.currentIndexChanged.connect(product_designation_changed)
        
        amount = QLineEdit()
        amount.setPlaceholderText("Mængde")
        amount.setFixedWidth(60)
        amount.setValidator(validator)

        article_number.currentIndexChanged.connect(self.reflect_selected_items)
        amount.editingFinished.connect(self.reflect_selected_items)

        self.rows.append((article_number, product_designation, amount))
        layout.addWidget(amount)

        return layout
    
    def sync_all_combo_box(self):
        self.block_reflect = True
        
        sorted_keys = sorted(sands.keys())
        sorted_values = [sands[key] for key in sorted_keys]

        for article_number, product_designation in [(row[0], row[1]) for row in self.rows]: # shallow copy
            prev_a_text = article_number.currentText()
            prev_p_text = product_designation.currentText()
            
            article_number.blockSignals(True)
            article_number.clear()
            article_number.addItems(sorted_keys)
            article_number.setCurrentIndex(-1)
            article_number.blockSignals(False)

            product_designation.blockSignals(True)
            product_designation.clear()
            product_designation.addItems(sorted_values)
            product_designation.setCurrentIndex(-1)
            product_designation.blockSignals(False)

            index = article_number.findText(prev_a_text)
            if index != -1:
                article_number.setCurrentIndex(index) # should automaticall make product_designation match.
            else:
                article_number.setCurrentText(prev_a_text)
                product_designation.setCurrentText(prev_p_text)
        
        self.block_reflect = False
        self.reflect_selected_items()
        

    def reflect_selected_items(self):
        if self.block_reflect: return

        totals = [0]*10
        weight = 0

        with get_session() as session:
            try:
                for row in self.rows:
                    article_number = row[0]
                    article_number_text = article_number.currentText()
                    amount = row[2]
                    this_weight = conv(amount.text())
                    if article_number.findText(article_number.currentText()) != -1:
                        if article_number_text not in self.sand_cache:
                            found_items = session.query(RawSandSieve).filter_by(item_id=article_number.currentText()).all()

                            self.sand_cache[article_number_text] = []
                            for sieve_item in found_items:
                                self.sand_cache[article_number_text].append(sieve_item)
                        
                        for sieve_item in self.sand_cache[article_number_text]:
                            totals[sieve_item.sieve.value] += sieve_item.sieve_gram * this_weight

                        if len(self.sand_cache[article_number_text]) > 0:
                            weight += this_weight
            finally:
                session.close()

        if weight != 0:
            for i in range(10):
                self.sieve_items[i].setText(stringify(round(totals[i] / weight, 2)))

    def clear_rows(self):
        self.block_reflect = True
        self.rows = []

        clear_layout(self.inner_container.layout())
        self.inner_container.layout().addLayout(self.getRow())

    def import_data(self):
        self.clear_rows()

        sets = get_sets()

        self.block_reflect = True
        last_insert_row = None
        for article_number, amount in sets:
            last_row = self.rows[len(self.rows)-1]

            index = last_row[0].findText(article_number)
            if index != -1:    
                last_row[0].setCurrentIndex(index) # try to place the id in - if it is right, it will add new one.
                last_row[2].setText(amount)

            last_insert_row = last_row

        if last_insert_row == self.rows[len(self.rows)-1]: #did not recognize the last one...
            last_insert_row[0].setCurrentText("")
            last_insert_row[2].setText("")
        self.block_reflect = False
        
        self.reflect_selected_items()

    def getList(self):
        return [conv(sieve_item.text()) for sieve_item in self.sieve_items[::-1]]
            

    def init_ui(self):
        layout = QHBoxLayout()
        
        self.inner_container = QWidget()
        self.inner_container.layout

        self.inner_layout = QVBoxLayout()
        self.inner_layout.setSpacing(10)
        self.inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.inner_container.setLayout(self.inner_layout)
        self.clear_rows()

        scroll_area = QScrollArea()
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(self.inner_container)
        scroll_area.setWidgetResizable(True)

        layout.addWidget(scroll_area)

        right_layout = QVBoxLayout()

        # Sieve table
        sieve_widget = QWidget()
        sieve_widget.setFixedWidth(180)

        sieve_layout = QGridLayout()
        sieve_layout.setColumnStretch(0, 0)
        sieve_layout.setColumnStretch(0, 1)
        sieve_layout.addWidget(QLabel("Sigte"), 0, 0)
        sieve_layout.addWidget(QLabel("Gennemfald %"), 0, 1)

        sieves = [
            "16 mm", "8 mm", "4 mm", "2 mm", "1 mm",
            "0,5 mm", "0,25 mm", "0,125 mm", "0,09 mm", "Bund"
        ]

        self.sieve_items = []
        for row, size in enumerate(sieves, start=1):
            sieve_layout.addWidget(QLabel(size), row, 0)
            sieve_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line_edit = QLineEdit()
            line_edit.setFixedWidth(80)
            line_edit.setEnabled(False)

            line_edit.textChanged.connect(lambda: self.updateCurve(self.getList()))

            sieve_layout.addWidget(line_edit, row, 1)
            self.sieve_items.append(line_edit)

        sieve_widget.setLayout(sieve_layout)
            
        right_layout.addWidget(sieve_widget)

        save_as_new_product = QPushButton("Gem som nyt produkt")
        save_as_new_product.clicked.connect(lambda: self.create_new_product(self.getList()))
        right_layout.addWidget(save_as_new_product) # run something like 'text, ok = QInputDialog.getText(None, "Oprete produkt", "Det nye produkts id")'?
                                                    # safeguards to not override, ofc.
                                                    # also option to go to said new product... somehow

        import_button = QPushButton("Importer data")
        import_button.clicked.connect(self.import_data)
        right_layout.addWidget(import_button)

        clear_button = QPushButton("Ryd")
        clear_button.clicked.connect(self.clear_rows)
        right_layout.addWidget(clear_button)

        right_layout.addSpacing(clear_button.sizeHint().height())
        drop_label = ExcelDropLabel(self)
        right_layout.addWidget(drop_label, stretch=1)
        right_layout.addSpacing(clear_button.sizeHint().height())

        kurve_button = QPushButton("Live kurve")
        kurve_button.clicked.connect(lambda: self.estimateCurve(self.getList()))
        right_layout.addWidget(kurve_button)
        layout.addLayout(right_layout)

        add_sand_event(self.sync_all_combo_box)
        addReloadEvent(self.sync_all_combo_box)

        def removeSand(sand): # or sand sieve
            if sand.item_id in self.sand_cache:
                del self.sand_cache[sand.item_id]
            return False
        add_sand_event([removeSand])
        add_sand_sieve_event([removeSand])

        def clearAndReflect():
            self.sand_cache.clear()
            self.reflect_selected_items()

        addReloadEvent(lambda: clearAndReflect())

        self.setLayout(layout)