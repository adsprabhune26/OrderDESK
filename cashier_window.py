from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import (
    QMessageBox,
    QPushButton,
    QAbstractItemView,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import QTimer, QDateTime
from datetime import datetime
import sqlite3


class CashierScreen(QtWidgets.QWidget):
    def __init__(self, login_window):
        super().__init__()
        uic.loadUi("cashierUI.ui", self)
        self.showMaximized()
        self.bill_items = {}
        self.selected_dish = None
        self.connect = sqlite3.connect("pos.db")
        self.daily_restock_check()
        self.bill_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.combos = [
            self.comboSnacks,
            self.comboBeverages,
            self.comboDesserts,
            self.comboFastFood,
            self.comboMainCourse,
            self.comboSouth,
        ]
        for combo in self.combos:
            combo.currentIndexChanged.connect(self.on_dish_selected)
        self.login_window = login_window
        self.add_button.clicked.connect(self.add_to_bill)
        self.confirm_button.clicked.connect(self.confirm_order)
        self.load_dishes("Snacks", self.comboSnacks)
        self.load_dishes("Beverages", self.comboBeverages)
        self.load_dishes("Desserts", self.comboDesserts)
        self.load_dishes("Fast Food", self.comboFastFood)
        self.load_dishes("Main Course", self.comboMainCourse)
        self.load_dishes("South Indian", self.comboSouth)

        for combo in self.combos:
            combo.setStyleSheet("""QComboBox{
                                background-color:#2F3E46;
	                            color:#F4F6F8;
                                }

                                QComboBox QAbstractItemView{
                                background-color:#2F3E46;
	                            color:#F4F6F8;
                                selection-background-color:#3E4F5F
                                }
                                """)

        self.quantity_spinbox.setMinimum(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateDateTime)
        self.timer.start(1000)
        self.updateDateTime()

        self.menu = QtWidgets.QMenu(self)
        self.actionViewOrders = self.menu.addAction("View Orders")
        self.actionLogout = self.menu.addAction("Logout")
        self.option_button.clicked.connect(self.show_options)
        self.actionViewOrders.triggered.connect(self.view_orders)
        self.actionLogout.triggered.connect(self.logout)

        self.menu.setStyleSheet("""QMenu {
                                background-color: #F4F6F8;
                                color: #2F3E46;                
                                border: 1px solid #2F3E46;        
                                }

                                QMenu::item {
                                background-color: transparent;
                                padding: 5px 20px;
                                }
                                
                                QMenu::item:selected {  
                                background-color: #2F3E46;        
                                color: #F4F6F8;                   
                                }""")

        self.opacity = QGraphicsOpacityEffect()
        self.opacity.setOpacity(0.5)
        self.label.setGraphicsEffect(self.opacity)

        self.opacity1 = QGraphicsOpacityEffect()
        self.opacity1.setOpacity(0.5)
        self.label_4.setGraphicsEffect(self.opacity1)

        self.opacity3 = QGraphicsOpacityEffect()
        self.opacity3.setOpacity(0.5)
        self.label_5.setGraphicsEffect(self.opacity3)

        self.opacity4 = QGraphicsOpacityEffect()
        self.opacity4.setOpacity(0.5)
        self.label_6.setGraphicsEffect(self.opacity4)

    def updateDateTime(self):
        now = QDateTime.currentDateTime()
        self.date_time_label.setText(now.toString("dd-MM-yyyy | hh:mm AP"))

    def show_options(self):
        self.menu.exec_(
            self.option_button.mapToGlobal(self.option_button.rect().bottomLeft())
        )

    def view_orders(self):
        self.orders_screen = viewOrderScreen()
        self.orders_screen.load_screen()

    def logout(self):
        self.close()
        self.login_window.username_entry.clear()
        self.login_window.password_entry.clear()
        self.login_window.show()
        self.login_window.username_entry.setFocus()

    def load_dishes(self, category, combo):
        combo.clear()
        combo.addItem(category)
        combo.model().item(0).setEnabled(False)

        cursor = self.connect.cursor()
        cursor.execute("Select dish_name From menu Where category = ?", (category,))
        for (dish,) in cursor.fetchall():
            combo.addItem(dish)

        cursor.close()

    def on_dish_selected(self):
        combo = self.sender()
        dish_name = combo.currentText()

        if not dish_name or dish_name in [
            "Snacks",
            "Beverages",
            "Desserts",
            "Fast Food",
            "Main Course",
            "South Indian",
        ]:
            return

        self.selected_dish = dish_name
        self.dish_label.setText(self.selected_dish)
        self.quantity_spinbox.setValue(1)

    def add_to_bill(self):
        dish_name = self.dish_label.text()
        quantity = self.quantity_spinbox.value()

        for combo in self.combos:
            combo.setCurrentIndex(0)

        if not dish_name:
            QMessageBox.warning(self, "Warning", "Please Select A Dish")
            return

        cursor = self.connect.cursor()
        cursor.execute(
            "Select id,price,current_stock from menu where dish_name=?", (dish_name,)
        )
        row = cursor.fetchone()
        item_ID, rate, curr_stock = row

        if curr_stock < quantity:
            QMessageBox.warning(self, "Out Of Stock", "Not Enough Stock")
            return

        amount = rate * quantity

        if item_ID in self.bill_items:
            self.bill_items[item_ID]["quantity"] += quantity
            self.bill_items[item_ID]["amount"] += amount
        else:
            self.bill_items[item_ID] = {
                "name": dish_name,
                "rate": rate,
                "quantity": quantity,
                "amount": amount,
            }

        self.selected_dish = None
        self.dish_label.clear()
        self.quantity_spinbox.setValue(1)

        self.bill_table.setColumnCount(6)
        self.bill_table.verticalHeader().setVisible(False)
        self.bill_table.setHorizontalHeaderLabels(
            ["ID", "Item", "Rate", "Quantity", "Amount", "Delete"]
        )
        self.bill_table.setRowCount(0)

        for row, (item_ID, item) in enumerate(self.bill_items.items()):
            self.bill_table.insertRow(row)

            self.bill_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item_ID)))
            self.bill_table.setItem(row, 1, QtWidgets.QTableWidgetItem(item["name"]))
            self.bill_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(str(item["rate"]))
            )
            self.bill_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(str(item["quantity"]))
            )
            self.bill_table.setItem(
                row, 4, QtWidgets.QTableWidgetItem(str(item["amount"]))
            )

            delete_btn = QtWidgets.QPushButton("Delete")
            delete_btn.setStyleSheet("""QPushButton {
  	                                    background-color:#2F3E46;
	                                    color:#F4F6F8;
                                        font-family:"Century751 No2 BT";
                                        font-size:11pt;
                                        font-weight:bold;
                                        font-style:italic;
                                    }

                                    QPushButton:hover {
                                        background-color:#253037;
                                    }

                                    QPushButton:pressed {
                                        background-color:#1B2327;
                                    }""")
            delete_btn.clicked.connect(lambda _, r=row: self.remove_item_from_bill(r))
            self.bill_table.setCellWidget(row, 5, delete_btn)

        self.update_totals()
        cursor.close()

    def remove_item_from_bill(self, row):
        item_id = int(self.bill_table.item(row, 0).text())

        if item_id in self.bill_items:
            del self.bill_items[item_id]

        self.bill_table.setRowCount(0)

        for row, (item_ID, item) in enumerate(self.bill_items.items()):
            self.bill_table.insertRow(row)

            self.bill_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item_ID)))
            self.bill_table.setItem(row, 1, QtWidgets.QTableWidgetItem(item["name"]))
            self.bill_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(str(item["rate"]))
            )
            self.bill_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(str(item["quantity"]))
            )
            self.bill_table.setItem(
                row, 4, QtWidgets.QTableWidgetItem(str(item["amount"]))
            )

            delete_btn = QtWidgets.QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, r=row: self.remove_item_from_bill(r))
            self.bill_table.setCellWidget(row, 5, delete_btn)

        self.update_totals()

    def refresh_delete_buttons(self):
        for row in range(self.bill_table.rowCount()):
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, r=row: self.remove_item_from_bill(r))
            self.bill_table.setCellWidget(row, 4, delete_btn)

    def update_totals(self):
        subtotal = 0
        for item in self.bill_items.values():
            subtotal += item["amount"]
        service_charge = subtotal * 0.05
        gst = subtotal * 0.05
        grand_total = subtotal + service_charge + gst

        self.subtotal_label.setText(f"Subtotal :{'':<61}₹ {subtotal:.2f}")
        self.service_charge_label.setText(
            f"Service Charge :{'':<51}₹ {service_charge:.2f}"
        )
        self.gst_label.setText(f"GST :{'':<67}₹ {gst:.2f}")
        self.grand_total_label.setText(f"Grand Total :{'':<55}₹ {grand_total:.2f}")

    def confirm_order(self):
        if not self.bill_items:
            QMessageBox.warning(self, "Warning", "No Items In The Bill")
            return

        now = datetime.now()
        order_date = now.strftime("%Y-%m-%d")
        order_time = now.strftime("%H:%M:%S")

        item_count = sum(item["quantity"] for item in self.bill_items.values())
        subtotal = sum(item["amount"] for item in self.bill_items.values())

        gst = round(subtotal * 0.05, 2)
        service_charge = round(subtotal * 0.05, 2)
        grand_total = round(subtotal + gst + service_charge, 2)

        cursor = self.connect.cursor()

        cursor.execute(
            "Insert Into orders(order_date,order_time,item_count,subtotal,gst,service_charge,grand_total) Values (?,?,?,?,?,?,?)",
            (
                order_date,
                order_time,
                item_count,
                subtotal,
                gst,
                service_charge,
                grand_total,
            ),
        )

        order_id = cursor.lastrowid

        for item_id, item in self.bill_items.items():
            cursor.execute(
                "Insert Into order_items (order_id, item_id, quantity, price) Values (?,?,?,?)",
                (order_id, item_id, item["quantity"], item["rate"]),
            )

        for item_id, item in self.bill_items.items():
            cursor.execute(
                "Insert Into order_items (order_id, item_id, quantity, price) Values (?,?,?,?)",
                (order_id, item_id, item["quantity"], item["rate"]),
            )

        cursor.execute(
            "Update menu Set current_stock=current_stock-? Where id=?",
            (item["quantity"], item_id),
        )

        self.connect.commit()

        self.bill_items.clear()
        self.bill_table.setRowCount(0)
        self.subtotal_label.setText("Subtotal :")
        self.service_charge_label.setText("Service Charge :")
        self.gst_label.setText("GST :")
        self.grand_total_label.setText("Grand Total :")

        QMessageBox.information(self, "Order Confirmed", "Order Placed Successfully")

    def daily_restock_check(self):
        today = datetime.now().strftime("%d-%m-%Y")
        cursor = self.connect.cursor()

        cursor.execute("Select value FROM system_state WHERE key='last_restock_date'")
        row = cursor.fetchone()

        if row is None or row[0] != today:
            cursor.execute("Update menu Set current_stock=daily_stock")

        cursor.execute(
            "Insert OR Replace Into system_state (key,value) Values ('last_restock_date',?)",
            (today,),
        )
        self.connect.commit()
        cursor.close()


class viewOrderScreen(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

    def load_screen(self):
        uic.loadUi("view_order_ui.ui", self)
        self.display_data()
        self.orders_table.verticalHeader().setVisible(False)
        self.orders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exec_()

    def display_data(self):
        connect = sqlite3.connect("pos.db")
        cursor = connect.cursor()
        cursor.execute(
            "Select order_id,order_date,order_time,item_count,grand_total from orders"
        )
        data = cursor.fetchall()
        connect.close()

        self.orders_table.setRowCount(len(data))
        self.orders_table.setColumnCount(5)
        headers = ["Order ID", "Date", "Time", "Total Items", "Total Amount"]
        self.orders_table.setHorizontalHeaderLabels(headers)

        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                self.orders_table.setItem(
                    row_index, col_index, QtWidgets.QTableWidgetItem(str(value))
                )
