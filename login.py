from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt
from manager_window import ManagerScreen
from cashier_window import CashierScreen
import sys
import sqlite3


class POS(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("login.ui", self)
        self.showMaximized()
        self.opacity = QGraphicsOpacityEffect()
        self.opacity.setOpacity(0.5)
        self.label.setGraphicsEffect(self.opacity)
        self.opacity1 = QGraphicsOpacityEffect()
        self.opacity1.setOpacity(0.5)
        self.label_2.setGraphicsEffect(self.opacity1)
        self.login_button.clicked.connect(self.login)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.login_button.click()

    def login(self):
        username = self.username_entry.text()
        password = self.password_entry.text()

        if not username or not password:
            QMessageBox.warning(self, "Warning", "Please enter username and password")
            return

        connect = sqlite3.connect("pos.db")
        cursor = connect.cursor()

        cursor.execute(
            "Select role From users Where username=? And password=?",
            (username, password),
        )
        result = cursor.fetchone()

        if result:
            if result[0] == "Manager":
                self.manager_screen = ManagerScreen(self)
                self.manager_screen.show()
            else:
                self.cashier_screen = CashierScreen(self)
                self.cashier_screen.show()
            self.hide()
        else:
            QMessageBox.warning(self, "Warning", "Incorrect Username or Password")


app = QtWidgets.QApplication(sys.argv)
window = POS()
window.show()
app.exec()
