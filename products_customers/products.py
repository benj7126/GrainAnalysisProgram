from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QPlainTextEdit, QDialog, QGridLayout
)
from PyQt6.QtCore import Qt
from sql import get_session, ProductSieve, Product, SieveSize, Batch, BatchSieve, UsedSand
from local_data import products, add_product_event, add_product_sieve_event, addReloadEvent
from sieve_builder import newSieve
from generate_curve import createCurve

from general_methods import conv, info_message_box, update_product_with_used_sand

# TODO: make all errors be from messages using some general message creation function
#       that is to say; don't make anything red (border things) cuz it dosen't work too well...

class P_Screen(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.init_ui()

        self.block_sql = False
    
    def update_remark(self):
        if self.block_sql: return
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        id = self.table_widget.item(ranges[0].topRow(), 0).text()
        with get_session() as session:
            try:
                product = session.query(Product).filter_by(product_id=id).first()
                product.remarks = self.remarks.toPlainText()
                session.commit()
            finally:
                session.close()


    def delete_item(self):
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        id = self.table_widget.item(ranges[0].topRow(), 0).text()
        name = self.table_widget.item(ranges[0].topRow(), 1).text()

        if QMessageBox.warning(self, "Fjern produkt", f'Fjern permanent {id} [{name}]?',
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                               QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No: return

        if QMessageBox.warning(self, "Helt sikker?", f'Dette slætter alle batches lavet ud fra {id} [{name}]. Fortsæt stadig?',
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                               QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No: return
        
        with get_session() as session:
            try:
                batches = session.query(Batch).filter_by(product_id=id).all()
                for batch in batches:
                    batch_sieves = session.query(BatchSieve).filter_by(batch_id=batch.batch_id).all()
                    for batch_sieve in batch_sieves:
                        session.delete(batch_sieve)

                    session.delete(batch)
                    
                sieves = session.query(ProductSieve).filter_by(product_id=id).all()
                for sieve in sieves:
                    session.delete(sieve)
                    
                usedSands = session.query(UsedSand).filter_by(used_in_product_id=id).all()
                for usedSand in usedSands:
                    session.delete(usedSand)

                product = session.query(Product).filter_by(product_id=id).first()
                session.delete(product)
                session.commit()
            finally:
                session.close()
        
        self.clear_product_values()
                
    def update_product_sieve(self, row):
        if self.block_sql: return
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        id = self.table_widget.item(ranges[0].topRow(), 0).text()

        with get_session() as session:
            try:
                sieve_limit = session.query(ProductSieve).filter_by(product_id=id, sieve=SieveSize(row)).first()
                if not sieve_limit:
                    sieve_limit = ProductSieve(product_id=id,sieve=SieveSize(row))
                    session.add(sieve_limit)
                
                sieve_limit.target_percentage = conv(self.sieve_items[row][0].text())
                sieve_limit.lower_bound_percentage = conv(self.sieve_items[row][1].text())
                sieve_limit.upper_bound_percentage = conv(self.sieve_items[row][2].text())

                session.commit()
            finally:
                session.close()

    def clear_product_values(self):
        self.block_sql = True
        
        self.remarks.setPlainText("")
        for col in self.sieve_items:
            for item in col:
                item.setText("")
                
        self.block_sql = False

    def stringify(self, val):
        return "" if val == -1 else (str(val) if val != int(val) else str(int(val)))

    def reflect_selected_item(self):
        if self.block_sql: return
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        self.clear_product_values()

        self.block_sql = True

        new_id = self.table_widget.item(ranges[0].topRow(), 0).text()
        with get_session() as session:
            try:
                product = session.query(Product).filter_by(product_id=new_id).first()
                self.remarks.setPlainText(product.remarks)
                for sieve_limit in session.query(ProductSieve).filter_by(product_id=new_id).all():
                    list = self.sieve_items[sieve_limit.sieve.value]

                    list[0].setText(self.stringify(sieve_limit.target_percentage))
                    list[1].setText(self.stringify(sieve_limit.lower_bound_percentage))
                    list[2].setText(self.stringify(sieve_limit.upper_bound_percentage))
                
                contains_sands = session.query(UsedSand).filter_by(used_in_product_id=new_id).count() > 0
                self.sand_types.setEnabled(contains_sands)
                self.recalc_seive_data.setEnabled(contains_sands)
            finally:
                session.close()

        self.block_sql = False

    def update_product_name(self, item):
        if self.block_sql: return
        if item.column() == 0: return

        text = ""
        if item:
            text = item.text()
        else:
            return

        with get_session() as session:
            id = self.table_widget.item(item.row(), 0).text()
            
            try:
                product = session.query(Product).filter_by(product_id=id).first()
                if product.product_name != text:
                    product.product_name = text
                    session.commit()
            finally:
                session.close()
    
    def update_product_list(self):
        self.block_sql = True

        selectedID = None
        ranges = self.table_widget.selectedRanges()
        if len(ranges) != 0:
            selectedID = self.table_widget.item(ranges[0].topRow(), 0).text()

        self.table_widget.clear()
        self.table_widget.setHorizontalHeaderLabels(["Produkt-ID", "Produkt-Navn"])
        self.table_widget.setRowCount(len(products))
        row_idx = 0
        for item_id, item in sorted(products.items()):
            id_item = QTableWidgetItem(item_id)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_widget.setItem(row_idx, 0, id_item)

            name_item = QTableWidgetItem(item["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table_widget.setItem(row_idx, 1, name_item)

            if item_id == selectedID:
                id_item.setSelected(True)
                name_item.setSelected(True)

            id_item.setData(Qt.ItemDataRole.UserRole, item_id)
            row_idx += 1
            
        self.block_sql = False
        
    def filter_table_items(self, id, name):
        if id == "" and name == "":
            for row in range(self.table_widget.rowCount()):
                self.table_widget.setRowHidden(row, False)
            return
        
        filter_id = id.lower()
        filter_name = name.lower()

        for row in range(self.table_widget.rowCount()):
            id_item = self.table_widget.item(row, 0)
            name_item = self.table_widget.item(row, 1)

            # Check if the search text is in either column's text
            # Only proceed if items exist (they should, based on your loading code)
            match_found = False
            if id_item and name_item:
                product_id = id_item.text().lower()
                product_name = name_item.text().lower()

                if (filter_id == "" or filter_id in product_id) and (filter_name == "" or filter_name in product_name):
                    match_found = True

            # Set the row visibility based on the match
            self.table_widget.setRowHidden(row, not match_found)

    def add_new_product(self):
        if self.new_id_text.text() == "":
            info_message_box(self, "Ugyldigt Input", "Der skal angives et ID.\nPrøv venligst igen.")
            return
        
        if self.new_id_text.text() in products.keys():
            info_message_box(self, "Ugyldigt Input", f"'{self.new_id_text.text()}' findes allerede. Angiv venligst et anden ID.")
            return

        with get_session() as session:
            try:
                self.new_id_text.setStyleSheet("")

                session.add(Product(
                    product_id=self.new_id_text.text(),
                    product_name=self.new_name_text.text()
                ))

                session.commit()

                self.new_id_text.setText("")
                self.new_name_text.setText("")
            finally:
                session.close()

    def init_ui(self):
        layout = QVBoxLayout()

        table_layout = QHBoxLayout()
        table_filter_layout = QVBoxLayout()
        self.table_widget = QTableWidget()

        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Produkt-ID", "Produkt-Navn"])
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        self.table_widget.itemChanged.connect(self.update_product_name)
        self.table_widget.itemSelectionChanged.connect(self.reflect_selected_item)

        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.resizeColumnsToContents()

        self.update_product_list()
        add_product_event(self.update_product_list)
        addReloadEvent(self.update_product_list)

        table_filter_layout.addWidget(self.table_widget)

        search_layout = QHBoxLayout()
        id_filter = QLineEdit()
        id_filter.setPlaceholderText("Produkt ID")
        id_filter.setFixedWidth(80)
        name_filter = QLineEdit()
        name_filter.setPlaceholderText("Produkt Navn")
        search_layout.addWidget(id_filter)
        search_layout.addWidget(name_filter)

        id_filter.textChanged.connect(lambda: self.filter_table_items(id_filter.text(), name_filter.text()))
        name_filter.textChanged.connect(lambda: self.filter_table_items(id_filter.text(), name_filter.text()))

        table_filter_layout.addLayout(search_layout)

        table_layout.addLayout(table_filter_layout)

        button_positioning = QVBoxLayout()
        new_button = QPushButton("Opret nyt produkt")
        new_button.clicked.connect(self.add_new_product)
        button_positioning.addWidget(new_button)
        self.new_id_text = QLineEdit()
        self.new_id_text.setPlaceholderText("Produkt ID*")
        self.new_id_text.setFixedWidth(120)
        button_positioning.addWidget(self.new_id_text)
        self.new_name_text = QLineEdit()
        self.new_name_text.setPlaceholderText("Produkt Navn")
        self.new_name_text.setFixedWidth(120)
        button_positioning.addWidget(self.new_name_text)
        button_positioning.addStretch(1)
        table_layout.addLayout(button_positioning)

        layout.addLayout(table_layout)

        layout.addSpacing(10)

        over_header_label = QLabel("Grænse-kornkurver")
        over_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(over_header_label)
        
        bottom_layout = QHBoxLayout()

        # Sieve table
        headers = ["Sigte", "Tilstræb %", "Nedre grænse %", "Øvre grænse %"]

        def add_update_product_sieve(line_edit, row, col):
            line_edit.editingFinished.connect(lambda current_row=row-1: self.update_product_sieve(current_row))
        
        sieve_widget, self.sieve_items = newSieve(headers, 90, add_update_product_sieve)
        
        
        def reflect_product_sieve_change(sieve_limit):
            ranges = self.table_widget.selectedRanges()
            if len(ranges) == 0: return

            product_id = self.table_widget.item(ranges[0].topRow(), 0).text()
            if sieve_limit.product_id != product_id: return

            self.block_sql = True
            list = self.sieve_items[sieve_limit.sieve.value]

            list[0].setText(self.stringify(sieve_limit.target_percentage))
            list[1].setText(self.stringify(sieve_limit.lower_bound_percentage))
            list[2].setText(self.stringify(sieve_limit.upper_bound_percentage))
            self.block_sql = False
            
            return False
        add_product_sieve_event([lambda sieve_limit: reflect_product_sieve_change(sieve_limit)])

        bottom_layout.addWidget(sieve_widget)

        bottom_layout.addSpacing(30)

        remarks_area = QVBoxLayout()

        remarks_area.addSpacing(9)
        remarks_area.addWidget(QLabel("Bemærkninger"))
        self.remarks = QPlainTextEdit()
        self.remarks.textChanged.connect(self.update_remark)
        remarks_area.addWidget(self.remarks)

        remarks_area.addSpacing(30)
        
        button_layout = QGridLayout()
        
        def show_sand_types():
            ranges = self.table_widget.selectedRanges()
            if len(ranges) == 0: return

            id = self.table_widget.item(ranges[0].topRow(), 0).text()

            dialog = UsedSandsDialog(id, self)
            dialog.exec()

        self.sand_types = QPushButton("Indeholder...")
        self.sand_types.clicked.connect(show_sand_types)
        self.sand_types.setEnabled(False)
        
        def call_update_PWUS():
            ranges = self.table_widget.selectedRanges()
            if len(ranges) == 0: return

            id = self.table_widget.item(ranges[0].topRow(), 0).text()

            update_product_with_used_sand(id)
            self.reflect_selected_item()

        self.recalc_seive_data = QPushButton("Genberegn kurve")
        self.recalc_seive_data.clicked.connect(call_update_PWUS)
        self.recalc_seive_data.setEnabled(False)

        def display_curve():
            ranges = self.table_widget.selectedRanges()
            if len(ranges) == 0: return

            name = self.table_widget.item(ranges[0].topRow(), 1).text()
            createCurve([conv(sieve_row[0].text()) for sieve_row in self.sieve_items[::-1]],
                        [conv(sieve_row[1].text()) for sieve_row in self.sieve_items[::-1]],
                        [conv(sieve_row[2].text()) for sieve_row in self.sieve_items[::-1]], name=name)

        
        button_layout = QGridLayout()
        see_curve = QPushButton("Se kurve")
        see_curve.clicked.connect(display_curve)

        delete = QPushButton("Slet")
        delete.clicked.connect(self.delete_item)

        button_layout.addWidget(self.sand_types, 0, 0)
        button_layout.addWidget(self.recalc_seive_data, 1, 0)
        button_layout.addWidget(see_curve, 0, 1)
        button_layout.addWidget(delete, 1, 1)

        remarks_area.addLayout(button_layout)

        bottom_layout.addLayout(remarks_area)

        layout.addLayout(bottom_layout)

        self.setLayout(layout)

class UsedSandsDialog(QDialog):
    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        
        self.setWindowTitle(f"Sand typer for {self.product_id}")
        self.setMinimumSize(600, 300)

        # Main layout
        layout = QVBoxLayout(self)

        # Create and configure the table widget
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(
            ["Varenr.", "Vare Betegnelse", "Recept Mængde", "Aktuel Procent (%)"]
        )
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Make table read-only
        
        # Style the header
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStyleSheet("font-weight: bold;")

        layout.addWidget(self.table_widget)

        # filter_table_items

        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept) # accept() closes the dialog
        layout.addWidget(close_button)

        self.setLayout(layout)
        
        # Populate the table with data
        self.load_data()

    def load_data(self):
        with get_session() as session:
            # Query the database for all sands used in the given product ID
            used_sands = session.query(UsedSand).filter_by(used_in_product_id=self.product_id).all()

            self.table_widget.setRowCount(len(used_sands))

            for row_index, sand in enumerate(used_sands):
                # Create QTableWidgetItem for each piece of data
                item_id = QTableWidgetItem(sand.item_id)
                designation = QTableWidgetItem(sand.product_designation)
                amount = QTableWidgetItem(f"{sand.amount:.2f}")
                percent = QTableWidgetItem(f"{sand.percent:.2f}%")
                
                # Add items to the table
                self.table_widget.setItem(row_index, 0, item_id)
                self.table_widget.setItem(row_index, 1, designation)
                self.table_widget.setItem(row_index, 2, amount)
                self.table_widget.setItem(row_index, 3, percent)