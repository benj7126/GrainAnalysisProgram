import sys
import pandas as pd
from general_methods import inner_create_new_product_or_update, info_message_box, sieve_data_from_components
from PyQt6.QtWidgets import QLabel, QProgressDialog
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal

import time

import os
import shutil
import tempfile
import ctypes
from ctypes import wintypes
import contextlib

FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
FILE_ATTRIBUTE_OFFLINE = 0x00001000

def is_online_only(file_path):
    if os.name != 'nt':
        return False # Assume local on Mac/Linux

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use ctypes to get file attributes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    GetFileAttributesW = kernel32.GetFileAttributesW
    GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    GetFileAttributesW.restype = wintypes.DWORD

    attrs = GetFileAttributesW(str(file_path))
    
    if attrs == 0xFFFFFFFF:
        return False

    # Check if either the "Recall on Data Access" or "Offline" bit is set
    is_cloud_file = (attrs & FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS) or \
                    (attrs & FILE_ATTRIBUTE_OFFLINE)
    
    return bool(is_cloud_file)

@contextlib.contextmanager
def ensure_local_file(file_path):
    original_path = os.path.abspath(file_path)
    temp_path = None
    
    # 1. Check if the file is Online-Only
    if is_online_only(original_path):
        # Create a temp file path with the same extension
        # delete=False is required temporarily until we copy the data
        suffix = os.path.splitext(original_path)[1]
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = tf.name
        tf.close()

        try:
            shutil.copyfile(original_path, temp_path)
            
            yield temp_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to process cloud file: {e}")
            
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    print("Temporary copy cleaned up.")
                except Exception as e:
                    print(f"Could not delete temp file {temp_path}: {e}")
    else:
        yield original_path

class ExcelDropLabel(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.setAcceptDrops(True)

        self.parent = parent
        self.thread = None
        self.worker = None
        
        self.setText("Masse importer fra excel fil.\nDrop her.")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                font-size: 14px;
                color: #555;
                background-color: #f0f0f0;
            }
            QLabel:hover {
                background-color: #e0e0e0;
                border-color: #777;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        
        for file_path in files:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                self.process_excel_file(file_path)
            else:
                info_message_box(None, "Fil type.", f"Invalid fil type: {file_path.split('/')[-1]}")

    def process_excel_file(self, input_file_path):
        with ensure_local_file(input_file_path) as file_path:
            try:
                df = pd.read_excel(file_path)
                
                data_as_dict = df.to_dict(orient='records')
                
                progressDialog = QProgressDialog(
                    "asd",
                    "asd",
                    0, 100, 
                    None
                )
                progressDialog.setWindowTitle("Excel importer")
                self.thread = QThread()
                self.worker = ProgressWorker()

                progressDialog.setMinimumDuration(0)
                progressDialog.setAutoClose(False)
                progressDialog.setValue(0)

                self.worker.moveToThread(self.thread)

                progressDialog.canceled.connect(self.worker.stop)
                
                self.thread.started.connect(lambda: self.worker.run_task(data_as_dict))
                self.worker.progress.connect(progressDialog.setValue)

                def update_text_lambda(text):
                    print(text, text.split("\\"))
                    progressDialog.setLabelText(text.split("\\")[0])
                    progressDialog.setCancelButtonText(text.split("\\")[1])
                self.worker.update_text.connect(update_text_lambda)

                update_text_lambda("Starter...\\Annuler")
                
                # self.worker.finished.connect(progressDialog.close)
                self.worker.finished.connect(self.thread.quit)
                self.thread.finished.connect(self.thread.deleteLater)
                self.worker.finished.connect(self.worker.deleteLater)
        
                self.thread.start()
                progressDialog.exec()
            
            except Exception as e:
                info_message_box(None, "Der skete en fejl", f"Encountered: {e}")

class ProgressWorker(QObject):
    # Signals for communication with the main thread
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    update_text = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run_task(self, data_as_dict):
        if not self._is_running:
            return
        
        self.update_text.emit("Skanner excel fil...\\Annuler")
        
        # transform to dict of products
        data_count = len(data_as_dict)
        counter = 0
        products_to_create = {}
        for item in data_as_dict:
            if not self._is_running:
                self.finished.emit()
                return
            counter = counter + 1
            self.progress.emit(int((counter / data_count) * 100))

            id = str(item['Styklistenr.'])

            if not id in products_to_create:
                products_to_create[id] = {
                    'name': str(item['Varebeskrivelse']),
                    'components': []
                }
            else:
                if products_to_create[id]['name'] != str(item['Varebeskrivelse']):
                    info_message_box(None, "Inkonsekvent input.", f"Forskellige varebeskrivelser for ID {id}:\n'{products_to_create[id]['name']}' og '{item['Varebeskrivelse']}.")
                    return
            
            products_to_create[id]['components'].append([str(item['Råvarenr.']), str(item['Råvarebeskrivelse']), item['Pr. 1000 KG']])

        if not self._is_running:
            self.finished.emit()
            return

        self.progress.emit(0)
        self.update_text.emit("Uploader nye/opdaterede produkter...\\Annuler")

        # match inputs for
        product_count = len(products_to_create)
        sand_cache = {}
        counter = 0
        for product in products_to_create:
            if not self._is_running:
                self.finished.emit()
                return
            counter = counter +  1
            self.progress.emit(int((counter / product_count) * 100))

            id = product
            name = products_to_create[product]['name']
            rows = products_to_create[id]['components']

            list, sand_cache = sieve_data_from_components(rows, sand_cache)
            
            inner_create_new_product_or_update(list, id, rows, name = name)
            
        self.update_text.emit(f"{counter} produkter oprettet/opdateret\\Luk")
        self.finished.emit()