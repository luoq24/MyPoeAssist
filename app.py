import sys
from PyQt6.QtWidgets import QApplication, QTabWidget, QMainWindow, QMessageBox
from PyQt6.QtGui import QFont, QIcon, QCloseEvent
import qdarktheme

from models.model import Model
from views.windows.item_helper import widgetItenHelper
from views.windows.mod_collect import widgetModCollect


PATH_ICON_APP = "data\\liemo.ico"
# PATH_ICON_APP = "G:\\logo icon\\huiz2.ico"


class AppPoeAssist(QMainWindow):

    def __init__(self):
        super().__init__()
        
        self.model = Model()

        self.tab_item_helper: widgetItenHelper = ...
        self.tab_mod_collect: widgetModCollect = ...

        self.init_ui()

    def init_ui(self):
        # self.setWindowIcon(QIcon(PATH_ICON_APP))
        self.setWindowTitle("剪贴板工具")
        self.setGeometry(100, 100, 500, 700)# 设置字体大小
        font = QFont()
        font.setPointSize(18)  # 设置字体大小
        self.setFont(font)

        # 创建 QTabWidget 并设置为主窗口的中央部件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_item_helper = widgetItenHelper(self.model)
        self.tab_widget.addTab(self.tab_item_helper, "道具")

        self.tab_mod_collect = widgetModCollect(self.model)
        self.tab_widget.addTab(self.tab_mod_collect, "收集Mod")

    def closeEvent(self, event: QCloseEvent):
        a = QMessageBox.question(
            self,
            '退出',
            '你确定要退出吗?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if a == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    app.setWindowIcon(QIcon(PATH_ICON_APP))
    watcher = AppPoeAssist()
    watcher.show()

    sys.exit(app.exec())
