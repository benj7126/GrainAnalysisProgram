
import re
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QVBoxLayout, QHBoxLayout, QGridLayout, QDateEdit, QSpacerItem, QMessageBox
)
from PyQt6.QtCore import QDate, Qt
from sql import get_session, BatchSieve, Batch, ProductSieve, Product, SieveSize
from local_data import add_product_event, products, add_product_sieve_event, add_customer_event, add_batch_event, batches, add_batch_sieve_event, addReloadEvent
from sieve_builder import newSieve
from generate_curve import createCurve
from build_pdf_reportlab import build_pdf

from comma_dot_verify import CommaDotDoubleValidator

from general_methods import conv, stringify, signals_blocked, get_list_item_or_none

from .shared import NR_D_Screen

sieves = [16, 8, 4, 2, 1, 0.5, 0.25, 0.125, 0.9, "Bund"]

all_batches = "[Alle Batches]"

class D_Screen(NR_D_Screen):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(main_window_ref, parent)

    def set_up_pdf(self):
        createCurve([conv(sieve_row[1].text()) for sieve_row in self.sieve_items[::-1]],
                    [conv(sieve_row[2].text()) for sieve_row in self.sieve_items[::-1]],
                    [conv(sieve_row[3].text()) for sieve_row in self.sieve_items[::-1]], None, None, True)
        
        data = {
            "date": self.date_edit.text(), # should this not be today..? seems weird for both to be the production date.
            "product_id": self.current_product_id,
            "product_name": self.product_name.text(),
            "batch_nr": self.current_batch_id,
            "batch_subnr": self.current_batch_iid, # not used but might be=
            "produced_date": self.date_edit.text(),
            "preformed_by": self.preformed_by.text(),
            "customer": self.customer_input.currentText(),
            "dust": self.dust_input.text(),
            "density": self.density_input.text()
        }

        rest_spread = 100
        spread = []

        for i in range(10):
            fallthrough = conv(self.sieve_items[i][1].text())
            new_spread = rest_spread - fallthrough
            spread.append(new_spread)

            rest_spread -= new_spread

        data["sieve_rows"] = []
        for idx, row in enumerate(self.sieve_items):
            data["sieve_rows"].append([sieves[idx], row[0].text(), spread[i], row[1].text(), row[2].text(), row[3].text()])

        build_pdf(data)

    def update_product_id_combo(self):
        self.product_id_combo.blockSignals(True)
        self.product_name.setText("")

        self.product_id_combo.clear()
        self.product_list = [all_batches]
        self.product_list.extend(sorted(products.keys()))
        self.product_id_combo.addItems(self.product_list)

        if self.current_product_id == None:
            new_index = -1
        else:
            new_index = self.product_id_combo.findText(self.current_product_id)
            
        self.product_id_combo.setCurrentIndex(new_index)
        
        self.product_id_combo.blockSignals(False)

    def update_id_combo(self):
        if not self.current_product_id: return

        if self.current_product_id not in products and self.current_product_id != all_batches:
            self.batch_id.clear(); self.batch_iid.clear(); self.current_product_id = None; return

        with signals_blocked(self.batch_id):
            saved = self.batch_id.currentText()

            self.batch_id.clear()
            if self.current_product_id != all_batches:
                self.batch_list = sorted(products[self.current_product_id]["batches"])
            else:
                self.batch_list = sorted([batch for product in products.values() for batch in product["batches"]])

            self.batch_id.addItems(self.batch_list)

            if saved in self.batch_list:
                self.batch_id.setCurrentIndex(self.batch_list.index(saved))
            else:
                self.batch_id.setCurrentIndex(0)

        self.on_batch_changed(self.batch_id.currentText())

    def update_iid_combo(self):
        if not self.current_product_id: return
        if not self.current_batch_id: return

        if self.current_batch_id not in batches:
            self.batch_iid.clear(); self.current_product_id = None; return

        with signals_blocked(self.batch_iid):
            saved = self.batch_iid.currentText()

            self.batch_iid.clear()
            self.batch_iid_list = sorted(batches[self.current_batch_id])
            
            if "original" in self.batch_iid_list:
                self.batch_iid_list.remove("original") # TODO: match what i call it other place
                self.batch_iid_list.insert(0, "original")

            self.batch_iid.addItems(self.batch_iid_list)
            
            if saved in self.batch_iid_list:
                self.batch_iid.setCurrentIndex(self.batch_iid_list.index(saved))
            else:
                self.batch_iid.setCurrentIndex(0)

        self.on_iid_changed(self.batch_iid.currentText())

    def update_batch_sieve(self, row):
        if not self.current_product_id: return
        if not self.current_batch_id: return
        if not self.current_batch_iid: return 

        with get_session() as session:
            try:
                sieve_results = session.query(BatchSieve).filter_by(batch_id=self.current_batch_id,
                                                                        batch_iid=self.current_batch_iid,
                                                                        sieve=SieveSize(row)).first()
                
                sieve_results.sieve_gram = conv(self.sieve_items[row][0].text())

                session.commit()
            finally:
                session.close()

        self.update_fall_through()

    def delete_batch(self):
        if not self.current_product_id: return
        if not self.current_batch_id: return
        if not self.current_batch_iid: return

        if QMessageBox.warning(self, "Fjern batch", f'Fjern permanent {self.current_batch_id} - {self.current_batch_iid}?',
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                               QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No: return
        
        with get_session() as session:
            try:
                batches = session.query(Batch).filter_by(batch_id=self.current_batch_id, batch_iid=self.current_batch_iid).all()
                for batch in batches:
                    batch_sieves = session.query(BatchSieve).filter_by(batch_id=self.current_batch_id, batch_iid=self.current_batch_iid).all()
                    for batch_sieve in batch_sieves:
                        session.delete(batch_sieve)

                    session.delete(batch)

                session.commit()
            finally:
                session.close()

    
    def database_update_value(self, update_lambda):
        if not self.current_product_id: return
        if not self.current_batch_id: return
        if not self.current_batch_iid: return
        
        with get_session() as session:
            try:
                batch = session.query(Batch).filter_by(batch_id=self.current_batch_id,
                                                       batch_iid=self.current_batch_iid).first()
                
                update_lambda(batch)

                session.commit()
            finally:
                session.close()
    
    def database_update_value_all_iids(self, update_lambda):
        if not self.current_product_id: return
        if not self.current_batch_id: return
        
        with get_session() as session:
            try:
                batches = session.query(Batch).filter_by(batch_id=self.current_batch_id).all()
                
                for batch in batches:
                    update_lambda(batch)

                session.commit()
            finally:
                session.close()
                
    def clear_product_values(self):
        for col in self.sieve_items:
            for i in range(1, 4):
                with signals_blocked(col[i]):
                    col[i].setText("")

        self.clear_batch_values()
    
    def clear_batch_values(self):
        for col in self.sieve_items:
            with signals_blocked(col[0]):
                col[0].setText("")

        with signals_blocked(self.production_area_1):
            self.production_area_1.setChecked(False)

        with signals_blocked(self.production_area_2):
            self.production_area_2.setChecked(False)

        with signals_blocked(self.customer_input):
            self.customer_input.setCurrentText("")

        with signals_blocked(self.date_edit):
            self.date_edit.setDate(QDate.currentDate())

        with signals_blocked(self.dust_input):
            self.dust_input.setText("")

        with signals_blocked(self.density_input):
            self.density_input.setText("")

        with signals_blocked(self.preformed_by):
            self.preformed_by.setText("")
            
        self.update_fall_through()

    
    def on_product_changed(self, text):
        self.batch_id.clear()
        self.batch_iid.clear()
        self.clear_product_values()

        product_index = self.product_id_combo.findText(text, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
        if product_index == -1: return

        self.current_product_id = get_list_item_or_none(self.product_list, product_index)
        if not self.current_product_id: return

        if self.current_product_id != all_batches:
            self.update_limits_for(self.current_product_id)
        
        self.update_id_combo()

    def update_limits_for(self, id):
        print("update for: " + id)
        with get_session() as session:
            try:
                product = session.query(Product).filter_by(product_id=id).first()

                product_name = product.product_name
                if self.current_product_id == all_batches:
                    product_name = id + " | " + product_name

                self.product_name.setText(product_name)
                for sieve_limit in session.query(ProductSieve).filter_by(product_id=id).all():
                    list = self.sieve_items[sieve_limit.sieve.value]

                    with signals_blocked(list[2]):
                        list[2].setText(stringify(sieve_limit.lower_bound_percentage))

                    with signals_blocked(list[3]):
                        list[3].setText(stringify(sieve_limit.upper_bound_percentage))

                session.commit()
            finally:
                session.close()

    
    def on_batch_changed(self, text):
        self.batch_iid.clear()
        if not self.current_product_id: return
        
        batch_index = self.batch_id.findText(text, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
        if batch_index == -1: return

        self.current_batch_id = get_list_item_or_none(self.batch_list, batch_index)

        if not self.current_batch_id: return

        tmp_product_limits = None;
        if self.current_product_id == all_batches:
            with get_session() as session:
                try:
                    batch = session.query(Batch).filter_by(batch_id=self.current_batch_id).first()
                    
                    tmp_product_limits = batch.product_id
                finally:
                    session.close()

            if tmp_product_limits:
                self.update_limits_for(tmp_product_limits)
            else:
                self.clear_product_values()

        # self.clear_batch_values()

        self.update_iid_combo()
    
    def on_iid_changed(self, text):
        if not self.current_product_id: return
        if not self.current_batch_id: return
        
        batch_index = self.batch_iid.findText(text, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
        if batch_index == -1: return

        last_batch_iid = self.current_batch_iid
        self.current_batch_iid = get_list_item_or_none(self.batch_iid_list, batch_index)

        if not self.current_batch_iid: return

        if self.current_batch_iid != last_batch_iid:
            self.clear_batch_values()

        self.block_sql = True
        
        with get_session() as session:
            try:
                batch = session.query(Batch).filter_by(batch_id=self.current_batch_id,
                                                       batch_iid=self.current_batch_iid).first()
                
                # batches = session.query(Batch).filter_by(batch_id=self.current_batch_id).all()
                
                sieve_results = session.query(BatchSieve).filter_by(batch_id=self.current_batch_id,
                                                                          batch_iid=self.current_batch_iid).all()
                for sieve_result in sieve_results:
                    self.sieve_items[sieve_result.sieve.value][0].setText(stringify(sieve_result.sieve_gram))
                
                self.production_area_1.setChecked(batch.production_area == 1)
                self.production_area_2.setChecked(batch.production_area == 2)
                
                self.date_edit.setDate(QDate(batch.production_date.year, batch.production_date.month, batch.production_date.day))
                self.customer_input.setEditText(batch.customer_name)
                self.dust_input.setText(stringify(batch.powder_percentage)),
                self.density_input.setText(stringify(batch.density))
                self.preformed_by.setText(batch.preformed_by)

                session.commit()
            finally:
                session.close()
                
        self.block_sql = False
        self.update_fall_through()

    def init_ui(self):
        layout = QVBoxLayout()

        # Top Fields
        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Produkt-ID"), 0, 0)
        self.product_list = []
        self.batch_list = []
        self.batch_iid_list = []
        self.product_id_combo = QComboBox()
        self.product_id_combo.setEditable(True)

        form_layout.addWidget(self.product_id_combo, 0, 1)

        form_layout.addWidget(QLabel("Produkt-Navn"), 1, 0)
        self.product_name = QLineEdit()
        self.product_name.setEnabled(False)
        form_layout.addWidget(self.product_name, 1, 1)
        
        self.update_product_id_combo()
        add_product_event(lambda: self.update_product_id_combo())
        self.product_id_combo.currentTextChanged.connect(self.on_product_changed)

        form_layout.addWidget(QLabel("Batch-nummer"), 2, 0)
        form_layout.addWidget(self.get_batch_date_widget(), 2, 1)
        
        form_layout.addWidget(QLabel("Kunde"), 3, 0)
        self.customer_input = QComboBox()
        self.customer_input.setEditable(True)
        self.customer_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # prevent adding new items
        self.update_customer_combo()
        self.customer_input.setCurrentIndex(-1)
        add_customer_event(lambda: self.update_customer_combo())
        
        def update_customer(batch):
            batch.customer_name = self.customer_input.currentText()
        self.customer_input.currentTextChanged.connect(lambda: self.database_update_value(update_customer))

        form_layout.addWidget(self.customer_input, 3, 1)

        form_layout.addWidget(QLabel("Pulverandel"), 4, 0)
        form_layout.addWidget(self.get_PDM_widget(), 4, 1)

        layout.addLayout(form_layout)


        bottom_layout = QHBoxLayout()

        # Sieve table
        headers = ["Sigte", "Sigterest gram", "Gennemfald %", "Nedre grænse %", "Øvre grænse %"]

        def dissableColsAndAddUpdates(line_edit, row, col):
            if col != 1:
                line_edit.setEnabled(False)
            else:
                line_edit.editingFinished.connect(lambda current_row=row-1: self.update_batch_sieve(current_row))
        
        sieve_widget, self.sieve_items = newSieve(headers, 80, dissableColsAndAddUpdates)
        
        def reflect_product_sieve_change(sieve_limit):
            if sieve_limit.product_id != self.current_product_id: return

            self.block_sql = True
            list = self.sieve_items[sieve_limit.sieve.value]

            list[2].setText(stringify(sieve_limit.lower_bound_percentage))
            list[3].setText(stringify(sieve_limit.upper_bound_percentage))
            self.block_sql = False
            
            return False
        add_product_sieve_event([lambda sieve_limit: reflect_product_sieve_change(sieve_limit)])
        
        
        def reflect_batch_sieve_change(sieve_result):
            if sieve_result.batch_id != self.current_batch_id: return
            if sieve_result.batch_iid != self.current_batch_iid: return

            self.block_sql = True
            self.sieve_items[sieve_result.sieve.value][0].setText(stringify(sieve_result.sieve_gram))
            self.block_sql = False
            return False
        add_batch_sieve_event([lambda sieve_result: reflect_batch_sieve_change(sieve_result)])

        bottom_layout.addWidget(sieve_widget)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.addStretch(1)
        print_button = QPushButton("Udskriv")
        print_button.clicked.connect(self.set_up_pdf) # TODO: make this open a thing that lets you place the pdf somewhere..?
        button_layout.addWidget(print_button)
        delete = QPushButton("Slet")
        delete.clicked.connect(self.delete_batch)
        button_layout.addWidget(delete)
        see_curve = QPushButton("Se kurve")
        see_curve.clicked.connect(lambda: createCurve([conv(sieve_row[1].text()) for sieve_row in self.sieve_items[::-1]],
                                                      [conv(sieve_row[2].text()) for sieve_row in self.sieve_items[::-1]],
                                                      [conv(sieve_row[3].text()) for sieve_row in self.sieve_items[::-1]]))
        button_layout.addWidget(see_curve)

        bottom_layout.addLayout(button_layout)

        layout.addLayout(bottom_layout)

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.addSpacerItem(QSpacerItem(400, 0))
        footer_layout.addWidget(QLabel("Udført af:"))
        self.preformed_by = QLineEdit()
        self.preformed_by.setMinimumWidth(200)
        self.preformed_by.setMaximumWidth(200)
        
        def update_preformed_by(batch):
            preformed_by = self.preformed_by.text()
            if preformed_by == "":
                self.preformed_by.setText(batch.preformed_by)
            else:
                batch.preformed_by = preformed_by

        self.preformed_by.editingFinished.connect(lambda: self.database_update_value(update_preformed_by))

        footer_layout.addWidget(self.preformed_by)
        layout.addLayout(footer_layout)
        
        # update batch values when batch is changed.
        add_batch_event([lambda batch: batch.product_id == self.current_product_id and batch.batch_id == self.current_batch_id and batch.batch_iid == self.current_batch_iid,
                       lambda: self.on_iid_changed(self.batch_iid.currentText())])

        self.setLayout(layout)
        
        addReloadEvent(self.update_product_id_combo)
        addReloadEvent(self.update_id_combo)
        addReloadEvent(self.update_iid_combo)

    def get_batch_date_widget(self):
        batch_and_date_layout = QHBoxLayout()
        batch_and_date_layout.setContentsMargins(0, 0, 0, 0)
        batch_and_date_layout.setSpacing(8)

        self.batch_id = QComboBox()
        self.batch_id.setEditable(True)
        self.batch_id.setMaximumWidth(80)
        self.batch_id.currentTextChanged.connect(self.on_batch_changed)
        batch_and_date_layout.addWidget(self.batch_id)  # Stretches to fill space

        self.batch_iid = QComboBox()
        self.batch_iid.setEditable(True)
        self.batch_iid.currentTextChanged.connect(self.on_iid_changed)
        batch_and_date_layout.addWidget(self.batch_iid, stretch=1)

        add_batch_event([lambda batch: batch.product_id == self.current_product_id and batch.batch_id == self.current_batch_id, self.update_iid_combo])
        add_batch_event([lambda batch: batch.product_id == self.current_product_id and batch.batch_id != self.current_batch_id, self.update_id_combo])

        batch_and_date_layout.addSpacing(10)    
        
        batch_and_date_layout.addWidget(QLabel("Produktionsdato"))
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy.MM.dd")
        self.date_edit.setCalendarPopup(True)

        self.date_edit.setFixedSize(self.date_edit.sizeHint())
        self.date_edit.setFixedWidth(120)
        
        def update_production_date(batch):
            batch.production_date = self.date_edit.date().toPyDate()
        self.date_edit.editingFinished.connect(lambda: self.database_update_value(update_production_date))
        # date_edit.setCalendarPopup(False)

        batch_and_date_layout.addWidget(self.date_edit)

        batch_date_widget = QWidget()
        batch_date_widget.setLayout(batch_and_date_layout)

        return batch_date_widget

    def get_PDM_widget(self):
        PDM_layout = QHBoxLayout()
        PDM_layout.setContentsMargins(0, 0, 0, 0)
        
        # PDM_layout.addWidget(QLabel("Pulverandel"))
        validator = CommaDotDoubleValidator()
        self.dust_input = QLineEdit()
        self.dust_input.setMaximumWidth(60)
        self.dust_input.setValidator(validator)
        
        def update_powder(batch):
            batch.powder_percentage = conv(self.dust_input.text())
        self.dust_input.editingFinished.connect(lambda: self.database_update_value(update_powder))

        PDM_layout.addWidget(self.dust_input)
        PDM_layout.addWidget(QLabel("gram"))
        
        PDM_layout.addSpacing(48)

        PDM_layout.addWidget(QLabel("Densitet"))
        self.density_input = QLineEdit()
        self.density_input.setMaximumWidth(100)
        self.density_input.setValidator(validator)
        
        def update_density(batch):
            batch.density = conv(self.density_input.text())
        self.density_input.editingFinished.connect(lambda: self.database_update_value(update_density))

        PDM_layout.addWidget(self.density_input)
        PDM_layout.addWidget(QLabel("kg/m³"))

        PDM_layout.addStretch(1)

        PDM_layout.addWidget(QLabel("Værk 1"))
        self.production_area_1 = QCheckBox()
        self.production_area_1.setChecked(False)
        PDM_layout.addWidget(self.production_area_1)
        
        PDM_layout.addSpacing(10)
        
        PDM_layout.addWidget(QLabel("Værk 2"))
        self.production_area_2 = QCheckBox()
        self.production_area_2.setChecked(False)
        PDM_layout.addWidget(self.production_area_2)
        
        def update_production_area(batch):
            batch.production_area = 1 if self.production_area_1.isChecked() else (2 if self.production_area_2.isChecked() else 0)

        def update_production_area_1(state):
            self.production_area_2.setChecked(False if state == Qt.CheckState.Checked else self.production_area_2.isChecked())
            self.database_update_value_all_iids(update_production_area)

        def update_production_area_2(state):
            self.production_area_1.setChecked(False if state == Qt.CheckState.Checked else self.production_area_1.isChecked())
            self.database_update_value_all_iids(update_production_area)

        self.production_area_1.checkStateChanged.connect(update_production_area_1)
        self.production_area_2.checkStateChanged.connect(update_production_area_2)
        PDM_layout.addSpacing(60)

        PDM_widget = QWidget()
        PDM_widget.setLayout(PDM_layout)

        return PDM_widget