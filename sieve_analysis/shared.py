from PyQt6.QtWidgets import (
    QWidget
)
from local_data import customers

from general_methods import stringify, conv

# TODO: This is neat, but might be slight overkill if i only have 3 methods...

class NR_D_Screen(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        
        self.current_product_id = None
        self.current_batch_id = None
        self.current_batch_iid = None

        self.init_ui()

    def update_customer_combo(self):
        self.customer_input.blockSignals(True)

        customer = self.customer_input.currentText()

        self.customer_input.clear()
        self.customer_input.addItems(sorted(customers))

        self.customer_input.setCurrentText(customer)

        self.customer_input.blockSignals(False)

    def update_fall_through(self):
        all_items = [conv(sub_arr[0].text()) for sub_arr in self.sieve_items]
        all_fields = [sub_arr[1] for sub_arr in self.sieve_items]
        
        lower_bounds = [conv(sub_arr[2].text()) for sub_arr in self.sieve_items]
        upper_bounds = [conv(sub_arr[3].text()) for sub_arr in self.sieve_items]
        
        item_sum = sum(all_items)
        
        acutal_sum = (item_sum + conv(self.dust_input.text()))
        
        if hasattr(self, "sieve_sum"):
            self.sieve_sum.setText(stringify(round(acutal_sum, 1)))

            if acutal_sum >= 99.5 and acutal_sum <= 100.5:
                self.sieve_sum.setStyleSheet(
                    "QLineEdit { background-color: #00ff00; color: black; }"
                )
            else:
                self.sieve_sum.setStyleSheet(
                    "QLineEdit { background-color: #ff0000; color: black; }"
                )
        
        total = 0.0
        for value, field, lower_bound, upper_bound in zip(all_items, all_fields, lower_bounds, upper_bounds):
            total += value

            fall_through = 100
            if total > 0:
                fall_through = round((1 - (total / item_sum)) * 100, 2)
            
            field.setText(str(fall_through))
            
            if fall_through < lower_bound or fall_through > upper_bound:
                field.setStyleSheet(
                    "QLineEdit { background-color: #ff0000; color: black; }"
                )
            else:
                field.setStyleSheet("")
        