from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from sql import get_session, Customer
from local_data import customers, add_customer_event, addReloadEvent

from general_methods import info_message_box

import pgeocode
nomis = ['DK', 'NO'] # others?

for i in range(0, len(nomis)):
    nomis[i] = pgeocode.Nominatim(nomis[i])

class C_Screen(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.init_ui()

        self.block_sql = False
    
    def guess_city(self):
        if len(self.postal.text()) != 4: return

        for i in range(0, len(nomis)):
            result = nomis[i].query_postal_code(self.postal.text())
            if type(result.place_name) is str:
                self.city.setText(result.place_name)
                return;

    def delete_item(self):
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        selectedCustomer = self.table_widget.item(ranges[0].topRow(), 0).text()

        if QMessageBox.warning(self, "Fjrern kunde", f'Fjern permanent {selectedCustomer}?',
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                               QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No: return
        
        with get_session() as session:
            try:
                customer = session.query(Customer).filter_by(customer_name=selectedCustomer).first()
                session.delete(customer)
                session.commit()
            finally:
                session.close()
        
        self.clear_customer_values()
            
                
    def update_customer_details(self): # could totally only have one for each of the fields.
        if self.block_sql: return
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        selectedCustomer = self.table_widget.item(ranges[0].topRow(), 0).text()

        with get_session() as session:
            try:
                customer = session.query(Customer).filter_by(customer_name=selectedCustomer).first()
                
                customer.customer_name = self.customer_name.text() 
                customer.customer_id = self.customer_id.text()
                customer.address = self.address.text()
                customer.postal = self.postal.text()
                customer.city = self.city.text()

                session.commit()
            finally:
                session.close()

            
    def clear_customer_values(self):
        self.block_sql = True
        
        self.customer_id.setText("")
        self.customer_name.setText("")
        self.address.setText("")
        self.postal.setText("")
        self.city.setText("")
                
        self.block_sql = False
        
    def reflect_selected_item(self):
        if self.block_sql: return
        ranges = self.table_widget.selectedRanges()
        if len(ranges) == 0: return

        self.clear_customer_values()

        self.block_sql = True

        selectedCustomer = self.table_widget.item(ranges[0].topRow(), 0).text()
        with get_session() as session:
            try:
                customer = session.query(Customer).filter_by(customer_name=selectedCustomer).first()
                
                self.customer_id.setText(customer.customer_id)
                self.customer_name.setText(customer.customer_name)
                self.address.setText(customer.address)
                self.postal.setText(customer.postal)
                self.city.setText(customer.city)

            finally:
                session.close()

        self.block_sql = False
    
    def update_customer_list(self):
        self.block_sql = True

        selectedCustomer = None
        ranges = self.table_widget.selectedRanges()
        if len(ranges) != 0:
            selectedCustomer = self.table_widget.item(ranges[0].topRow(), 0).text()

        self.table_widget.clear()
        self.table_widget.setHorizontalHeaderLabels(["Kunder"])
        self.table_widget.setRowCount(len(customers))
        row_idx = 0
        for item_name in sorted(customers):
            customer_item = QTableWidgetItem(str(item_name))
            customer_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

            customer_item.setFlags(customer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_widget.setItem(row_idx, 0, customer_item)

            if item_name == selectedCustomer:
                customer_item.setSelected(True)

            customer_item.setData(Qt.ItemDataRole.UserRole, item_name)
            row_idx += 1

        self.block_sql = False

    def add_new_customer(self):
        if self.new_customer_name.text() == "":
            info_message_box(self, "Ugyldigt Input", "Der skal angives et navn.\nPrøv venligst igen.")
            return
        
        if self.new_customer_name.text() in customers:
            info_message_box(self, "Ugyldigt Input", f"'{self.new_customer_name.text()}' findes allerede. Angiv venligst et andet navn.")
            return

        with get_session() as session:
            try:
                self.new_customer_name.setStyleSheet("")

                session.add(Customer(
                    customer_name=self.new_customer_name.text(),
                ))

                session.commit()

                self.new_customer_name.setText("")
            finally:
                session.close()

    def init_ui(self):
        layout = QVBoxLayout()

        table_layout = QHBoxLayout()
        self.table_widget = QTableWidget()

        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_widget.setColumnCount(1)
        self.table_widget.setHorizontalHeaderLabels(["Kunder"])
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        self.table_widget.itemChanged.connect(self.update_customer_details)
        self.table_widget.itemSelectionChanged.connect(self.reflect_selected_item)

        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.resizeColumnsToContents()

        self.update_customer_list()
        add_customer_event(self.update_customer_list)
        addReloadEvent(self.update_customer_list)

        table_layout.addWidget(self.table_widget)

        button_positioning = QVBoxLayout()
        new_customer = QPushButton("Opret ny kunde")
        new_customer.clicked.connect(self.add_new_customer)
        button_positioning.addWidget(new_customer)
        self.new_customer_name = QLineEdit()
        # new_id_text.setStyleSheet("border: 1px solid red;") - an idea for input missing?
        self.new_customer_name.setPlaceholderText("Kunde*")
        self.new_customer_name.setFixedWidth(120)
        button_positioning.addWidget(self.new_customer_name)
        
        button_positioning.addStretch(1)

        delete = QPushButton("Slet")
        delete.clicked.connect(self.delete_item)
        button_positioning.addWidget(delete)

        table_layout.addLayout(button_positioning)

        layout.addLayout(table_layout)

        info_area = QVBoxLayout()
        id_and_name = QHBoxLayout()
        info_area.addWidget(QLabel("Kunde"))

        self.customer_id = QLineEdit() # TODO: So, what was this about again..?
        self.customer_id.setFixedWidth(30)
        self.customer_id.setEnabled(True)
        self.customer_id.setPlaceholderText("ID")
        self.customer_id.setMaxLength(2)
        self.customer_id.editingFinished.connect(self.update_customer_details)
        id_and_name.addWidget(self.customer_id)
        self.customer_name = QLineEdit()
        self.customer_name.setEnabled(False)
        self.customer_name.editingFinished.connect(self.update_customer_details)
        id_and_name.addWidget(self.customer_name)
        info_area.addLayout(id_and_name)
        
        self.address = QLineEdit()
        self.address.setPlaceholderText("Address")
        self.address.editingFinished.connect(self.update_customer_details)
        info_area.addWidget(self.address)

        city_and_postal = QHBoxLayout()
        self.postal = QLineEdit()
        self.postal.setMaxLength(4)
        self.postal.setPlaceholderText("Postnummer")
        self.postal.setFixedWidth(80)
        self.postal.textChanged.connect(self.guess_city)
        self.postal.editingFinished.connect(self.update_customer_details)
        city_and_postal.addWidget(self.postal)
        self.city = QLineEdit()
        self.city.setPlaceholderText("By") # try to set this automatically using 'geopy'?
        self.city.editingFinished.connect(self.update_customer_details)
        city_and_postal.addWidget(self.city)
        info_area.addLayout(city_and_postal)

        layout.addLayout(info_area)

        self.setLayout(layout)
