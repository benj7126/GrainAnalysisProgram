import sys
import time
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog, QComboBox, QVBoxLayout, QHBoxLayout, QGridLayout, QDateEdit, QSpacerItem, QCheckBox
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal, pyqtSlot
from sql import get_session, BatchSieve, Batch, ProductSieve, Product, SieveSize
from local_data import add_product_event, add_product_sieve_event, add_customer_event, batches, addReloadEvent

from comma_dot_verify import CommaDotDoubleValidator

from sieve_builder import newSieve
from generate_curve import createCurve
from general_methods import conv, info_message_box, stringify

from .shared import NR_D_Screen

# do i need/want a list for batches ^^?

def get_new_iid(batch_iids):
    for i in range(1, 1000): # more than enough, lol
        if i not in batch_iids:
            return i

class NR_Screen(NR_D_Screen):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(main_window_ref, parent)
        
        self.batch_dialog = QInputDialog()
        self.batch_dialog.setWindowTitle("Genbrugt batch id")
        self.batch_dialog.setOkButtonText("Opret") # Set the text for the OK button
        self.batch_dialog.setCancelButtonText("Annuler") # Set the text for the Cancel button
                
    def clear_product_values(self):
        for col in self.sieve_items:
            for i in range(1, 4):
                col[i].setText("")
    
    def clear_batch_values(self):
        for col in self.sieve_items:
            col[0].setText("")
            col[1].setText("")

        self.customer_input.setCurrentText("")
        self.batch_id.setText("")
        self.date_edit.setDate(QDate.currentDate())
        self.dust_input.setText("")
        self.density_input.setText("")
        self.preformed_by.setText("")

        self.production_area_1.setChecked(False)
        self.production_area_2.setChecked(False)

    def batch_lock_production_area(self):
        if self.batch_id.text() in batches:
            locked_in_production_area = None
            with get_session() as session:
                try:
                    batch = session.query(Batch).filter_by(batch_id=self.batch_id.text()).first()

                    locked_in_production_area = batch.production_area
                finally:
                    session.close()
            
            if locked_in_production_area:
                self.production_area_1.setEnabled(False)
                self.production_area_2.setEnabled(False)
                self.production_area_1.setChecked(locked_in_production_area == 1)
                self.production_area_2.setChecked(locked_in_production_area == 2)
        else:
            if (not self.production_area_1.isEnabled()) or (not self.production_area_2.isEnabled()):
                self.production_area_1.setEnabled(True)
                self.production_area_2.setEnabled(True)
                self.production_area_1.setChecked(False)
                self.production_area_2.setChecked(False)

    
    def on_product_index_changed(self, change):
        self.current_product_id = self.product_list[change]

        if not self.current_product_id: return

        self.clear_product_values()

        with get_session() as session:
            try:
                product = session.query(Product).filter_by(product_id=self.current_product_id).first()
                
                self.product_name.setText(product.product_name)
                for sieve_limit in session.query(ProductSieve).filter_by(product_id=self.current_product_id).all():
                    list = self.sieve_items[sieve_limit.sieve.value]

                    # list[1].setText(stringify(sieve_limit.target_percentage))
                    list[2].setText(stringify(sieve_limit.lower_bound_percentage))
                    list[3].setText(stringify(sieve_limit.upper_bound_percentage))

                session.commit()
            finally:
                session.close()

        self.update_fall_through()

    def get_new_idd(self, batch_iids, batch_id):
        self.batch_dialog.setLabelText(f'Batch [{batch_id}] eksistere allerade.\nAngiv unik identifikator:')
        while True:
            if self.batch_dialog.exec():
                text = self.batch_dialog.textValue()

                if text.strip() == "":
                    QMessageBox.warning(None, "Ugyldigt Input", "Der skal angives en identifikator.\nPrøv venligst igen.")
                elif text in batch_iids:
                    QMessageBox.warning(None, "Ugyldigt Input", f"'{text}' er allerade i brug. Angiv venligst en anden identifikator.")
                else:
                    return text
            else:
                return False

    def save_batch(self):
        if self.current_product_id == None:
            info_message_box(self, "Ugyldigt Input", "Der er ikke blevet valgt et produkt.")
            return
        
        batch_id = self.batch_id.text()
        if batch_id == "":
            info_message_box(self, "Ugyldigt Input", "Skal angives et batch id.")
            return

        with get_session() as session:
            fetched_batches = session.query(Batch).filter_by(batch_id=batch_id).all()

            for batch_product_id in [batch.product_id for batch in fetched_batches]:
                if batch_product_id != self.current_product_id:
                    QMessageBox.warning(None, "Ugyldigt Input", "Dette batch id anvendes allerade for et andet produkt.")
                    return

        for col in self.sieve_items:
            if col[0].text() == "":
                QMessageBox.warning(None, "Ugyldigt Input", "Alle sigte værdier skal udfyldes.")
                return
            
        preformed_by = self.preformed_by.text()
        if preformed_by == "":
            QMessageBox.warning(None, "Ugyldigt Input", "[Udført af] feltet skal udfyldes.")
            return
        
        with get_session() as session:
            try:
                if self.production_area_1.isChecked():
                    production_area = 1
                elif self.production_area_2.isChecked():
                    production_area = 2
                else:
                    QMessageBox.warning(None, "Værk fejl", "Skal vælge et værk for batchet.")
                    return

                if batch_id not in batches:
                    new_iid = "original" # TODO: what to call this?
                else:
                    new_iid = self.get_new_idd(batches[batch_id], batch_id)
                
                if not new_iid:
                    session.close()
                    return

                session.add(Batch(
                    batch_id = batch_id,
                    batch_iid = new_iid,
                    product_id = self.current_product_id,
                    production_area = production_area,
                    customer_name = self.customer_input.currentText(),
                    production_date = self.date_edit.date().toPyDate(),
                    powder_percentage = conv(self.dust_input.text()),
                    density = conv(self.density_input.text()),
                    preformed_by = preformed_by
                ))

                for sieve in SieveSize:
                    session.add(BatchSieve(batch_id=batch_id,
                                                 batch_iid=new_iid,
                                                 production_area = production_area,
                                                 sieve=sieve,
                                                 sieve_gram=conv(self.sieve_items[sieve.value][0].text())))
                
                session.commit()
            finally:
                session.close()
            
        self.clear_batch_values()

    def init_ui(self):
        layout = QVBoxLayout()

        # Top Fields
        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Produkt-ID"), 0, 0)
        self.product_list = []
        # self.batch_list = []
        self.product_id_combo = QComboBox()
        self.product_id_combo.setEditable(True)

        self.product_id_combo.currentIndexChanged.connect(self.on_product_index_changed)
        
        form_layout.addWidget(self.product_id_combo, 0, 1)

        form_layout.addWidget(QLabel("Produkt-Navn"), 1, 0)
        self.product_name = QLineEdit()
        self.product_name.setEnabled(False)
        form_layout.addWidget(self.product_name, 1, 1)

        self.update_product_id_combo()
        add_product_event(self.update_product_id_combo)
        addReloadEvent(self.update_product_id_combo)

        form_layout.addWidget(QLabel("Batch-nummer"), 2, 0)
        form_layout.addWidget(self.get_batch_date_widget(), 2, 1)
        
        form_layout.addWidget(QLabel("Kunde"), 3, 0) # should be able to figure out based on 2 first chars of id.
        self.customer_input = QComboBox()
        self.customer_input.setEditable(True)
        self.customer_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # prevent adding new items
        self.update_customer_combo()
        self.customer_input.setCurrentIndex(-1)
        add_customer_event(lambda: self.update_customer_combo())

        form_layout.addWidget(self.customer_input, 3, 1)

        form_layout.addWidget(QLabel("Pulverandel"), 4, 0)
        form_layout.addWidget(self.get_PDM_widget(), 4, 1)

        layout.addLayout(form_layout)


        bottom_layout = QHBoxLayout()

        headers = ["Sigte", "Sigterest gram", "Gennemfald %", "Nedre grænse %", "Øvre grænse %"]

        def dissableCols(line_edit, row, col):
            if col != 1:
                line_edit.setEnabled(False)
            elif col == 1:
                line_edit.editingFinished.connect(lambda: self.update_fall_through())
        
        sieve_widget, self.sieve_items = newSieve(headers, 80, dissableCols)


        def reflect_product_sieve_change(sieve_limit):
            index = self.product_id_combo.findText(self.product_id_combo.currentText(), Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
            if index == -1: return

            self.current_product_id = self.product_list[index]

            if sieve_limit.product_id != self.current_product_id: return

            self.block_sql = True
            list = self.sieve_items[sieve_limit.sieve.value]

            list[1].setText(stringify(sieve_limit.target_percentage))
            list[2].setText(stringify(sieve_limit.lower_bound_percentage))
            list[3].setText(stringify(sieve_limit.upper_bound_percentage))
            self.block_sql = False
            
            return False

        add_product_sieve_event([lambda sieve_limit: reflect_product_sieve_change(sieve_limit)])

        bottom_layout.addWidget(sieve_widget)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.addStretch(1)
        new_batch = QPushButton("Gem")
        new_batch.clicked.connect(self.save_batch)
        button_layout.addWidget(new_batch)
        clear = QPushButton("Ryd")
        clear.clicked.connect(self.clear_product_values)
        clear.clicked.connect(self.clear_batch_values)
        button_layout.addWidget(clear)

        see_curve = QPushButton("Se kurve")
        button_layout.addWidget(see_curve)
        see_curve.clicked.connect(lambda: createCurve([conv(sieve_row[1].text()) for sieve_row in self.sieve_items[::-1]],
                                                      [conv(sieve_row[2].text()) for sieve_row in self.sieve_items[::-1]],
                                                      [conv(sieve_row[3].text()) for sieve_row in self.sieve_items[::-1]]))
        
        bottom_layout.addLayout(button_layout)

        layout.addLayout(bottom_layout)

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.addWidget(QLabel("Sum:"))
        self.sieve_sum = QLineEdit()
        self.sieve_sum.setEnabled(False)
        self.sieve_sum.setMaximumWidth(30)
        footer_layout.addWidget(self.sieve_sum)
        footer_layout.addSpacerItem(QSpacerItem(20, 0))

        sieves = [
            "16 mm", "8 mm", "4 mm", "2 mm", "1 mm",
            "0,5 mm", "0,25 mm", "0,125 mm", "0,09 mm", "Bund"
        ]

        def pasteAndNext(thread, value):
            found_focus = False
            for i in range(10):
                if found_focus == True:
                    self.sieve_items[i][0].setFocus()
                    return
                
                if self.sieve_items[i][0].hasFocus():
                    self.sieve_items[i][0].setText(value)
                    thread.send_to_display(sieves[i])
                    found_focus = True
        
        footer_layout.addWidget(QLabel("Vægt-status:"))
        self.weight_connect = QPushButton("Ikke forbundet")
        self.weight_connect.setFixedWidth(100)

        def tryConnectScale(button):
            if self.weight_connect.text() != "Ikke forbundet":
                if self.thread:
                    self.thread.stop()
                return
            
            self.thread = ScaleThread()
            self.thread.button = self.weight_connect
            self.thread.weight_received.connect(lambda value: pasteAndNext(self.thread, value))
            self.thread.start()

        self.weight_connect.clicked.connect(tryConnectScale)
        footer_layout.addWidget(self.weight_connect)

        footer_layout.addSpacerItem(QSpacerItem(130, 0))
        footer_layout.addWidget(QLabel("Udført af:"))
        self.preformed_by = QLineEdit()
        self.preformed_by.setFixedWidth(200)
        
        footer_layout.addWidget(self.preformed_by)
        layout.addLayout(footer_layout)

        self.setLayout(layout)


    def get_batch_date_widget(self):
        batch_and_date_layout = QHBoxLayout()
        batch_and_date_layout.setContentsMargins(0, 0, 0, 0)
        batch_and_date_layout.setSpacing(8)

        self.batch_id = QLineEdit()
        batch_and_date_layout.addWidget(self.batch_id, stretch=1)  # Stretches to fill space
        self.batch_id.editingFinished.connect(self.batch_lock_production_area)

        batch_and_date_layout.addSpacing(10)
        
        batch_and_date_layout.addWidget(QLabel("Produktionsdato"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy.MM.dd")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(120)
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

        self.dust_input.editingFinished.connect(lambda: self.update_fall_through())

        PDM_layout.addWidget(self.dust_input)
        PDM_layout.addWidget(QLabel("gram"))
        
        PDM_layout.addSpacing(48)

        PDM_layout.addWidget(QLabel("Densitet"))
        self.density_input = QLineEdit()
        self.density_input.setMaximumWidth(100)
        self.density_input.setValidator(validator)
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

        self.production_area_1.checkStateChanged.connect(lambda state: self.production_area_2.setChecked(False if state == Qt.CheckState.Checked else self.production_area_2.isChecked()))
        self.production_area_2.checkStateChanged.connect(lambda state: self.production_area_1.setChecked(False if state == Qt.CheckState.Checked else self.production_area_1.isChecked()))
        PDM_layout.addSpacing(60)

        PDM_widget = QWidget()
        PDM_widget.setLayout(PDM_layout)

        return PDM_widget
    
class ScaleThread(QThread):
    weight_received = pyqtSignal(str)
    button = None
    is_running = False

    def stop(self):
        self.is_running = False
        
    @pyqtSlot(str)
    def send_to_display(self, text):
        return
#        if self.ser and self.ser.is_open:
#            time.sleep(1.5) 
#    
#            # 2. Clear the buffers to ensure the 'pipe' is empty
#            self.ser.reset_input_buffer()
#            self.ser.reset_output_buffer()
#            
#            # 3. Send the command that gave the 'L' response
#            # We add a leading \r\n to 'wake up' the listener
#            self.ser.write(b"\r\nD TEST\r\n")
#            cmds = [
#                b"M TEST\r\n", 
#                b"MT TEST\r\n", 
#                b"DT TEST\r\n", 
#                b"D TEST\r\n", 
#                b"I5 TEST\r\n", 
#                b"DISP TEST\r\n",
#                b"MT 1 TEST\r\n"
#            ]
#
#            for c in cmds:
#                print(f"Trying command: {c.decode().strip()}")
#                self.ser.write(c)
#                time.sleep(0.1) # Look at the scale now!
#
#            # command = f"IP {text[:7]}\r\n" 
#            # self.ser.write("DM HELLO".encode('ascii'))


    def run(self):
        self.button.setText("Forbinder...")
        ports = serial.tools.list_ports.comports()
        port = ""

        for p in ports:
            if "VID:PID=0403:6015" in p.hwid: # TODO: add a setting for setting this value - like i want to with connections to sql and such
                port = p.device
            

        if port != "":
            self.is_running = True
            self.button.setText("Forbundet")

        while self.is_running:
            baud = 9600
            
            try:
                self.ser = serial.Serial(port, baud, timeout=0.2)
                result = ""
                while self.is_running:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('ascii').strip()

                        parts = line.split()
                                
                        if len(parts) == 2 and parts[1] == 'g':
                            result = parts[0]
                            self.weight_received.emit(result) # if response is wanted, remove dis line.

#                        if "Verified By:" in line:
#                            while True:
#                                extra = self.ser.readline()
#                                if not extra: # If nothing comes for 0.5s, it's truly over
#                                    break
#                                
#                            self.weight_received.emit(result)

            except Exception as e:
                self.is_running = False
                print(f"Serial Error: {e}")
            finally:
                pass
        
        self.button.setText("Ikke forbundet")


# Example output
# 1/11/2026               12:11:11
# Balance ID: *******
# Balance Type: *******
# Balance Name: *******
# User Name:
# Project Name:
# Weighing
# 9.9     g
# Gross:        9.9     g    G
# Net:        9.9     g    N
# Tare:        0.0     g    T
# Signature:____________
# Verified By:____________