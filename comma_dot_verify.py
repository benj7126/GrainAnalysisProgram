from PyQt6.QtGui import QValidator
from PyQt6.QtWidgets import QApplication, QLineEdit

class CommaDotDoubleValidator(QValidator):
    def __init__(self, parent=None):
        super().__init__(parent)

    def validate(self, input_str, pos):
        if input_str == "":
            return QValidator.State.Intermediate, input_str, pos

        # Replace ',' with '.' for numeric checks
        s = input_str.replace(',', '.')

        # Only allow one decimal point
        if s.count('.') > 1:
            return QValidator.State.Invalid, input_str, pos

        # Check numeric characters
        allowed_chars = "0123456789."
        if not all(c in allowed_chars for c in s):
            return QValidator.State.Invalid, input_str, pos

        # Check if it's a valid float
        try:
            float(s)
            return QValidator.State.Acceptable, input_str, pos
        except ValueError:
            return QValidator.State.Intermediate, input_str, pos