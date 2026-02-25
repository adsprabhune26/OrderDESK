from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import QTimer, QDateTime
from PyQt5.QtWidgets import (
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QGraphicsOpacityEffect,
)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from datetime import datetime

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

import sqlite3

import tempfile

import os


class ManagerScreen(QtWidgets.QWidget):
    def __init__(self, login_window):
        super().__init__()
        uic.loadUi("managerUI.ui", self)
        self.showMaximized()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateDateTime)
        self.timer.start(500)
        self.updateDateTime()

        self.connect = sqlite3.connect("pos.db")

        self.opacity = QGraphicsOpacityEffect()
        self.opacity.setOpacity(0.5)
        self.label_2.setGraphicsEffect(self.opacity)

        self.opacity1 = QGraphicsOpacityEffect()
        self.opacity1.setOpacity(0.5)
        self.label_3.setGraphicsEffect(self.opacity1)

        self.opacity3 = QGraphicsOpacityEffect()
        self.opacity3.setOpacity(0.5)
        self.label_10.setGraphicsEffect(self.opacity3)

        self.no_orders_label.hide()
        self.report_frame.hide()
        self.calendar.selectionChanged.connect(self.on_date_selected)
        self.canvas = None

        self.scroll_area = QtWidgets.QScrollArea(self.report_frame)
        self.scroll_area.setGeometry(self.report_data_frame.geometry())
        self.scroll_area.setWidget(self.report_data_frame)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.report_data_frame.setMinimumHeight(1000)

        self.daily_restock_check()
        self.load_combobox()
        self.column_combo.currentIndexChanged.connect(self.on_column_selected)
        self.category_combo_2.hide()

        # Apply stylesheet to combo boxes for proper disabled item handling
        combo_boxes = [
            self.category_combo,
            self.category_combo_2,
            self.update_item_combo,
            self.column_combo,
            self.delete_item_combo,
        ]
        for combo in combo_boxes:
            combo.setStyleSheet("""QComboBox{
                                background-color:#F4F6F8;
                                color:#2F3E46;
                                }

                                QComboBox QAbstractItemView{
                                background-color:#F4F6F8;
                                color:#2F3E46;
                                selection-background-color:#DCE2E9
                                }
                                """)

        self.pdf_button.clicked.connect(self.generate_pdf)
        self.add_item_button.clicked.connect(self.add_item)
        self.update_item_button.clicked.connect(self.update_item)
        self.delete_item_button.clicked.connect(self.delete_item)

        self.menu = QtWidgets.QMenu(self)
        self.actionViewMenu = self.menu.addAction("View Menu")
        self.actionViewOrders = self.menu.addAction("View Orders")
        self.actionLogout = self.menu.addAction("Logout")
        self.login_window = login_window
        self.option_button.clicked.connect(self.show_options)
        self.actionLogout.triggered.connect(self.logout)
        self.actionViewOrders.triggered.connect(self.view_orders)
        self.actionViewMenu.triggered.connect(self.view_menu)

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

    def show_options(self):
        self.menu.exec_(
            self.option_button.mapToGlobal(self.option_button.rect().bottomLeft())
        )

    def view_orders(self):
        self.orders_screen = viewOrderScreen()
        self.orders_screen.load_screen()

    def view_menu(self):
        self.menu_screen = viewMenuScreen()
        self.menu_screen.load_screen()

    def updateDateTime(self):
        now = QDateTime.currentDateTime()
        self.date_time_label.setText(now.toString("dd-MM-yyyy | hh:mm AP"))

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

    def on_date_selected(self):
        self.report_frame.show()

        selected_date = self.calendar.selectedDate()
        db_date = selected_date.toString("yyyy-MM-dd")
        date_text = selected_date.toString("dd-MM-yyyy")
        day_text = selected_date.toString("dddd")

        cursor = self.connect.cursor()
        total_orders = cursor.execute(
            "Select count(*) from orders where order_date=?", (db_date,)
        ).fetchone()[0]
        if not total_orders:
            self.no_orders_label.show()
            if self.canvas:
                self.canvas.setParent(None)
                self.canvas = None
        else:
            self.no_orders_label.hide()
            if self.canvas:
                self.canvas.setParent(None)
                self.canvas = None

            cursor.execute(
                """Select m.category,sum(oi.quantity) from orders o Join order_items oi On o.order_id=oi.order_id
                           Join menu m On oi.item_id=m.id Where o.order_date=? Group By m.category""",
                (db_date,),
            )
            data = cursor.fetchall()

            categories = []
            quantities = []

            for row in data:
                categories.append(row[0])
                quantities.append(row[1])

            self.fig = Figure(figsize=(5, 8), dpi=100)
            ax = self.fig.add_subplot(111)
            ax.bar(categories, quantities)
            ax.set_ylim(bottom=0)
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_title("Category-Wise Items Sold")
            ax.set_ylabel("Quantity")
            ax.set_xlabel("Category")
            ax.tick_params(axis="x", rotation=45)
            self.fig.subplots_adjust(bottom=0.25)
            self.canvas = FigureCanvas(self.fig)
            self.canvas.setParent(self.report_data_frame)
            self.canvas.setGeometry(0, 266, 440, 500)
            self.canvas.draw()
            self.canvas.show()

        sold_items = cursor.execute(
            "Select sum(item_count)from orders where order_date=?", (db_date,)
        ).fetchone()[0]
        sold_items = sold_items if sold_items else 0

        subtotal = cursor.execute(
            "Select sum(subtotal)from orders where order_date=?", (db_date,)
        ).fetchone()[0]
        subtotal = subtotal if subtotal else 0

        gst = cursor.execute(
            "Select sum(gst)from orders where order_date=?", (db_date,)
        ).fetchone()[0]
        gst = gst if gst else 0

        service_charge = cursor.execute(
            "Select sum(service_charge)from orders where order_date=?", (db_date,)
        ).fetchone()[0]
        service_charge = service_charge if service_charge else 0

        grand_total = cursor.execute(
            "Select sum(grand_total)from orders where order_date=?", (db_date,)
        ).fetchone()[0]
        grand_total = grand_total if grand_total else 0

        self.date_label.setText(date_text)
        self.day_label.setText(day_text)
        self.total_orders_label.setText(f"{total_orders}")
        self.total_items_label.setText(f"{sold_items}")
        self.subtotal_label.setText(f"{subtotal}")
        self.total_gst_label.setText(f"{gst}")
        self.serviice_charge_label.setText(f"{service_charge}")
        self.grand_total_label.setText(f"{grand_total}")

    def generate_pdf(self):
        today = self.date_label.text()
        default_name = f"dailyReport{today}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", default_name, "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        pdf = SimpleDocTemplate(file_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        title = Paragraph("<b>Daily Sales Report</b>", styles["Title"])
        elements.append(title)
        elements.append(Spacer(1, 15))
        date_text = Paragraph(
            f"Date: <b>{self.date_label.text()}</b>" f"({self.day_label.text()})",
            styles["Normal"],
        )

        elements.append(date_text)
        elements.append(Spacer(1, 20))
        elements.append(
            Paragraph(
                f"Total Orders:{self.total_orders_label.text()}", styles["Normal"]
            )
        )
        elements.append(
            Paragraph(
                f"Total Items Sold:{self.total_items_label.text()}", styles["Normal"]
            )
        )
        elements.append(
            Paragraph(f"Day Subtotal:{self.subtotal_label.text()}", styles["Normal"])
        )
        elements.append(
            Paragraph(f"Total GST:{self.total_gst_label.text()}", styles["Normal"])
        )
        elements.append(
            Paragraph(
                f"Total Service Charge:{self.serviice_charge_label.text()}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(f"Grand Total:{self.grand_total_label.text()}", styles["Normal"])
        )
        elements.append(Spacer(1, 25))
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        self.fig.savefig(temp_img.name, dpi=150)
        graph = Image(temp_img.name, width=400, height=250)
        elements.append(graph)
        pdf.build(elements)
        temp_img.close()
        try:
            os.unlink(temp_img.name)
        except FileNotFoundError:
            pass

        QMessageBox.information(self, "Success", "PDF generated successfully!")

    def load_combobox(self):
        cursor = self.connect.cursor()

        self.category_combo.clear()
        self.category_combo.addItem("Select Category")
        self.category_combo.model().item(0).setEnabled(False)
        cursor.execute("Select Distinct category From menu order by category")
        categories = cursor.fetchall()
        for cat in categories:
            self.category_combo.addItem(cat[0])

        self.category_combo_2.clear()
        self.category_combo_2.addItem("Select Category")
        self.category_combo_2.model().item(0).setEnabled(False)
        for cat in categories:
            self.category_combo_2.addItem(cat[0])

        cursor.execute("Select id,dish_name From menu order by dish_name")
        items = cursor.fetchall()

        self.update_item_combo.clear()
        self.update_item_combo.addItem("Select Item")
        self.update_item_combo.model().item(0).setEnabled(False)
        for item_id, dish_name in items:
            self.update_item_combo.addItem(dish_name, item_id)

        self.column_combo.clear()
        self.column_combo.addItem("Select Column")
        self.column_combo.model().item(0).setEnabled(False)
        columns = [
            ("Dish Name", "dish_name"),
            ("Category", "category"),
            ("Price", "price"),
            ("Daily Stock", "daily_stock"),
        ]
        for label, column in columns:
            self.column_combo.addItem(label, column)

        self.delete_item_combo.clear()
        self.delete_item_combo.addItem("Select Item")
        self.delete_item_combo.model().item(0).setEnabled(False)
        for item_id, dish_name in items:
            self.delete_item_combo.addItem(dish_name, item_id)

        cursor.close()

    def add_item(self):
        item_name = self.name_entry.text()
        category_index = self.category_combo.currentIndex()
        category = self.category_combo.currentText()
        price = self.price_entry.text()
        daily_stock = self.stock_entry.text()
        current_stock = daily_stock

        if not item_name or not price or not daily_stock:
            QMessageBox.warning(self, "Error", "All Fields Are Mandatory")
            return

        if category_index == 0:
            QMessageBox.warning(self, "Error", "Please Select A Valid Category")
            return

        if not price.isdigit():
            QMessageBox.warning(self, "Error", "Price Must Be A Number")
            return

        if not daily_stock.isdigit():
            QMessageBox.warning(self, "Error", "Daily Stock Must Be A Number")
            return

        cursor = self.connect.cursor()
        cursor.execute(
            "Insert Into menu (category,dish_name,price,daily_stock,current_stock) Values (?,?,?,?,?)",
            (category, item_name, price, daily_stock, current_stock),
        )
        self.connect.commit()
        cursor.close()

        self.name_entry.clear()
        self.price_entry.clear()
        self.stock_entry.clear()
        self.category_combo.setCurrentIndex(0)

        QMessageBox.information(self, "Success", "Item Added Successfully")
        self.load_combobox()

    def on_column_selected(self):
        column_name = self.column_combo.currentData()

        if column_name == "category":
            self.new_value_entry.hide()
            self.category_combo_2.show()
        else:
            self.category_combo_2.setCurrentIndex(0)
            self.new_value_entry.show()
            self.category_combo_2.hide()

    def update_item(self):
        item_index = self.update_item_combo.currentIndex()
        item_id = self.update_item_combo.currentData()
        column_index = self.column_combo.currentIndex()
        column_name = self.column_combo.currentData()
        new_val = self.new_value_entry.text()
        category_index = self.category_combo_2.currentIndex()
        category = self.category_combo_2.currentText()

        if item_index == 0:
            QMessageBox.warning(self, "Error", "Please Select An Item")
            return

        if column_index == 0:
            QMessageBox.warning(self, "Error", "Please Select A Column")
            return

        if column_name == "category" and category_index == 0:
            QMessageBox.warning(self, "Error", "Please Select Category")
            return

        if column_name != "category" and not new_val:
            QMessageBox.warning(self, "Error", "Value Cannot Be Empty")
            return

        cursor = self.connect.cursor()

        if column_name == "daily_stock":
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("Select count(*) from orders where order_date=?", (today,))
            data = cursor.fetchone()[0]

            if not data:
                if not new_val.isdigit():
                    QMessageBox.warning(self, "Error", "Daily Stock Must Be A Number")
                    return

                cursor.execute(
                    f"Update menu Set {column_name}=?,current_stock=? Where id=?",
                    (new_val, new_val, item_id),
                )
                self.connect.commit()
                cursor.close()

                self.update_item_combo.setCurrentIndex(0)
                self.column_combo.setCurrentIndex(0)
                self.new_value_entry.clear()

                QMessageBox.information(
                    self, "Success", "Daily Stock Updated Successfully"
                )
                return

            else:
                cursor.execute(
                    """Select coalesce (sum(oi.quantity),0) 
                               from order_items oi JOIN orders o on oi.order_id=o.order_id 
                               Where oi.item_id=? And o.order_date=?""",
                    (item_id, today),
                )
                sold_quantity = cursor.fetchone()[0]

                if not new_val.isdigit():
                    QMessageBox.warning(self, "Error", "Daily Stock Must Be A Number")
                    return

                new_daily_stock = int(new_val)

                if new_daily_stock >= sold_quantity:
                    new_current_stock = new_daily_stock - sold_quantity

                    cursor.execute(
                        "Update menu set daily_stock=?,current_stock=? Where id=?",
                        (new_daily_stock, new_current_stock, item_id),
                    )
                    self.connect.commit()
                    cursor.close()

                    self.update_item_combo.setCurrentIndex(0)
                    self.column_combo.setCurrentIndex(0)
                    self.new_value_entry.clear()

                    QMessageBox.information(
                        self, "Success", "Daily Stock Updated Successfully"
                    )
                    return
                else:
                    QMessageBox.warning(
                        self,
                        "Invaid",
                        "Daily Stock Cannot Be Less than Already Sold Items",
                    )
                    cursor.close()
                    return

        elif column_name == "category":

            cursor.execute(
                f"Update menu Set {column_name}=? Where id=?", (category, item_id)
            )
            self.connect.commit()
            cursor.close()

            self.update_item_combo.setCurrentIndex(0)
            self.column_combo.setCurrentIndex(0)
            self.category_combo_2.setCurrentIndex(0)
            self.category_combo_2.hide()
            self.new_value_entry.show()

            QMessageBox.information(
                self, "Success", "Item Category Updated Successfully"
            )

        elif column_name == "price":
            if not new_val.isdigit():
                QMessageBox.warning(self, "Error", "Price Must Be A Number")
                return

            cursor.execute(
                f"Update menu Set {column_name}=? Where id=?", (new_val, item_id)
            )
            self.connect.commit()
            cursor.close()

            self.update_item_combo.setCurrentIndex(0)
            self.column_combo.setCurrentIndex(0)
            self.new_value_entry.clear()

            QMessageBox.information(self, "Success", "Item Price Updated Successfully")
            return

        else:
            cursor.execute(
                f"Update menu Set {column_name}=? Where id=?", (new_val, item_id)
            )
            self.connect.commit()
            cursor.close()

            self.update_item_combo.setCurrentIndex(0)
            self.column_combo.setCurrentIndex(0)
            self.new_value_entry.clear()

            QMessageBox.information(self, "Success", "Item Name Updated Successfully")
        self.load_combobox()

    def delete_item(self):
        item_index = self.delete_item_combo.currentIndex()

        if item_index == 0:
            QMessageBox.warning(self, "Error", "Please Select An Item To Delete")
            return

        item_id = self.delete_item_combo.currentData()

        cursor = self.connect.cursor()
        cursor.execute("Delete From menu Where id=?", (item_id,))
        cursor.close()
        self.connect.commit()

        self.delete_item_combo.setCurrentIndex(0)

        # Reload comboboxes to reflect deletion
        self.load_combobox()

        QMessageBox.information(self, "Success", "Item Deleted Successfully")

    def logout(self):
        self.close()
        self.login_window.username_entry.clear()
        self.login_window.password_entry.clear()
        self.login_window.show()
        self.login_window.username_entry.setFocus()


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
            "Select order_id,order_date,order_time,item_count,subtotal,gst,service_charge,grand_total from orders"
        )
        data = cursor.fetchall()
        connect.close()

        self.orders_table.setRowCount(len(data))
        self.orders_table.setColumnCount(8)
        headers = [
            "Order ID",
            "Date",
            "Time",
            "Total Items",
            "Subtotal",
            "GST",
            "Service Charge",
            "Grand Total",
        ]
        self.orders_table.setHorizontalHeaderLabels(headers)

        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                self.orders_table.setItem(
                    row_index, col_index, QtWidgets.QTableWidgetItem(str(value))
                )


class viewMenuScreen(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

    def load_screen(self):
        uic.loadUi("view_menu_ui.ui", self)
        self.display_data()
        self.menu_table.verticalHeader().setVisible(False)
        self.menu_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exec_()

    def display_data(self):
        connect = sqlite3.connect("pos.db")
        cursor = connect.cursor()
        cursor.execute(
            "Select id,dish_name,category,price,daily_stock,current_stock from menu"
        )
        data = cursor.fetchall()
        connect.close()

        self.menu_table.setRowCount(len(data))
        self.menu_table.setColumnCount(6)
        headers = [
            "Item ID",
            "Name",
            "Category",
            "Price",
            "Daily Stock",
            "Current Stock",
        ]
        self.menu_table.setHorizontalHeaderLabels(headers)

        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                self.menu_table.setItem(
                    row_index, col_index, QtWidgets.QTableWidgetItem(str(value))
                )
