from PyQt6.QtWidgets import QLabel, QLineEdit, QGridLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QLocale

from comma_dot_verify import CommaDotDoubleValidator
validator = CommaDotDoubleValidator()

def newSieve(headers, maxWidth, modify_line_edit):
    sieve_layout = QGridLayout()
    sieve_items = []
    
    sieves = [
        "16 mm", "8 mm", "4 mm", "2 mm", "1 mm",
        "0,5 mm", "0,25 mm", "0,125 mm", "0,09 mm", "Bund"
    ]
    
    for i, header in enumerate(headers):
        header_label = QLabel(header)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sieve_layout.addWidget(header_label, 0, (i+1)*2-2)

    for row, size in enumerate(sieves, start=1):
        sieve_layout.addWidget(QLabel(size), row, 0)
        sieve_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        list = []
        for col in range(1, len(headers)):
            line_edit = QLineEdit()
            line_edit.setMaximumWidth(maxWidth)
            line_edit.setValidator(validator)

            modify_line_edit(line_edit, row, col)

            list.append(line_edit)
            
            sieve_layout.addWidget(line_edit, row, col*2)
            sieve_layout.setColumnStretch(col*2-1, 1)

        sieve_items.append(list)

    sieve_widget = QWidget()
    sieve_widget.setLayout(sieve_layout)

    widgets_to_order = []
    num_rows = len(sieves)
    num_cols = len(headers) - 1
    
    for col in range(num_cols):
        for row in range(num_rows):
            widgets_to_order.append(sieve_items[row][col])
    
    for i in range(len(widgets_to_order) - 1):
        sieve_widget.setTabOrder(widgets_to_order[i], widgets_to_order[i+1])
    
    return sieve_widget, sieve_items