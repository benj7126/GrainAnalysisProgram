from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from sql import get_session, RawSand, RawSandSieve, SieveSize
from local_data import sands, addReloadEvent, add_sand_event

from comma_dot_verify import CommaDotDoubleValidator

from general_methods import stringify, conv, info_message_box, signals_blocked, newline_strip

class RS_Screen(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.modifying = 0

        self.current_id = None
        
        self.init_ui()

    def add_new_sand(self):
        if self.new_id_text.text() == "":
            info_message_box(self, "Ugyldigt Input", "Der skal angives et Varenr.")
            return
        
        if self.new_id_text.text() in sands.keys():
            info_message_box(self, "Ugyldigt Input", "Varenr. findes allerede Angiv venligst et anden Varenr.")
            return

        with get_session() as session:
            try:
                session.add(RawSand(
                    item_id=newline_strip(self.new_id_text.text().upper()),
                    product_designation=newline_strip(self.new_name_text.text())
                ))

                session.commit()

                self.new_id_text.setText("")
                self.new_name_text.setText("")
            finally:
                session.close()

    def clear_sand_values(self):
        for sieve_item in self.sieve_items:
            with signals_blocked(sieve_item):
                sieve_item.setText("")

    def delete_selected_item(self):
        if not self.current_id: return

        self.clear_sand_values()

        with get_session() as session:
            try:
                sand = session.query(RawSand).filter_by(item_id=self.current_id).first()
                session.delete(sand)

                sand_sieves = session.query(RawSandSieve).filter_by(item_id=self.current_id).all()
                for sieve in sand_sieves:
                    session.delete(sieve)
                    
                session.commit()
            finally:
                session.close()
                self.current_id = None

    def reflect_selected_item(self):
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0:
            for sieve_item in self.sieve_items: sieve_item.setEnabled(False)
            return
        
        for sieve_item in self.sieve_items: sieve_item.setEnabled(True)

        self.clear_sand_values()

        self.current_id = self.table_widget.item(ranges[0].topRow(), 0).text()
        with get_session() as session:
            try:
                for sieve_item in session.query(RawSandSieve).filter_by(item_id=self.current_id).all():
                    with signals_blocked(self.sieve_items[sieve_item.sieve.value]):
                        self.sieve_items[sieve_item.sieve.value].setText(stringify(sieve_item.sieve_gram))
            finally:
                session.close()

    def update_sand_name(self, item): # TODO: random crash issue - feels like a thread problem :/
        if item.column() == 0: return

        text = ""
        if item:
            text = item.text()
        else:
            return

        with get_session() as session:
            try:
                sand = session.query(RawSand).filter_by(item_id=self.current_id).first()
                if sand.product_designation != text:
                    sand.product_designation = text
                    session.commit()
            finally:
                session.close()
    
    def update_sand_list(self):
        with signals_blocked(self.table_widget):
            self.table_widget.setRowCount(0)
            self.table_widget.setRowCount(len(sands))
            row_idx = 0
            for item_id, product_designation in sorted(sands.items()):
                id_item = QTableWidgetItem(item_id)
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table_widget.setItem(row_idx, 0, id_item)

                name_item = QTableWidgetItem(product_designation)
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table_widget.setItem(row_idx, 1, name_item)

                if item_id == self.current_id:
                    id_item.setSelected(True)
                    name_item.setSelected(True)

                id_item.setData(Qt.ItemDataRole.UserRole, item_id)
                row_idx += 1
        
        self.reflect_selected_item()
                
    def update_product_sieve(self, row):
        if not self.current_id: return

        with get_session() as session:
            try:
                raw_sand_sieve = session.query(RawSandSieve).filter_by(item_id=self.current_id, sieve=SieveSize(row)).first()
                if not raw_sand_sieve:
                    raw_sand_sieve = RawSandSieve(item_id=self.current_id, sieve=SieveSize(row))
                    session.add(raw_sand_sieve)
                
                raw_sand_sieve.sieve_gram = conv(self.sieve_items[row].text())

                session.commit()
            finally:
                session.close()

    def init_ui(self):
        layout = QHBoxLayout()
        self.table_widget = QTableWidget()

        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Varenr.        ", "Varebetegnelse"])
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        self.table_widget.itemChanged.connect(self.update_sand_name)
        self.table_widget.itemSelectionChanged.connect(self.reflect_selected_item)

        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.resizeColumnsToContents()

        add_sand_event(self.update_sand_list)
        addReloadEvent(self.update_sand_list)
        

        layout.addWidget(self.table_widget)

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

        validator = CommaDotDoubleValidator()
        for row, size in enumerate(sieves, start=1):
            sieve_layout.addWidget(QLabel(size), row, 0)
            sieve_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line_edit = QLineEdit()
            line_edit.setFixedWidth(80)
            line_edit.setValidator(validator)
            line_edit.setEnabled(False)
            
            line_edit.editingFinished.connect(lambda current_row=row-1: self.update_product_sieve(current_row))

            sieve_layout.addWidget(line_edit, row, 1)
            self.sieve_items.append(line_edit)

        sieve_widget.setLayout(sieve_layout)
            
        right_layout.addWidget(sieve_widget)
        
        add_button = QPushButton("Tilføj ny råvare")
        add_button.clicked.connect(self.add_new_sand)
        right_layout.addWidget(add_button)
        self.new_id_text = QLineEdit()
        # new_id_text.setStyleSheet("border: 1px solid red;") - an idea for input missing?
        self.new_id_text.setPlaceholderText("Varenr.*")
        self.new_id_text.setFixedWidth(180)
        right_layout.addWidget(self.new_id_text)
        self.new_name_text = QLineEdit()
        self.new_name_text.setPlaceholderText("Varebetegnelse")
        self.new_name_text.setFixedWidth(180)
        right_layout.addWidget(self.new_name_text)
        right_layout.addStretch(1)
        delete_sand = QPushButton("Fjerne råvare")
        delete_sand.clicked.connect(self.delete_selected_item)
        right_layout.addWidget(delete_sand)
        layout.addLayout(right_layout)

        layout.addLayout(layout)
        layout.addLayout(right_layout)

        self.update_sand_list()

        self.setLayout(layout)