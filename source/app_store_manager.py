import ctypes
import sys

# 尽早初始化 OLE，避免 Qt 创建 QApplication 时 OleInitialize 失败导致剪贴板报错
ctypes.windll.ole32.OleInitialize(None)

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtGui import QFont, QIcon, QCloseEvent
import qdarktheme

from models.store_manager import StoreManager
from tools.hotkey import GlobalHotkeyFilter, VK_F2, VK_F3, VK_F4
from views.windows.store_manager import widgetStoreManager


PATH_ICON_APP = "data\\liemo.ico"


class AppStoreManager(QMainWindow):

    def __init__(self):
        super().__init__()

        self.model = StoreManager()

        self.tab_store_manager: widgetStoreManager = ...
        self._hotkey_f2: GlobalHotkeyFilter = ...
        self._hotkey_f3: GlobalHotkeyFilter = ...
        self._hotkey_f4: GlobalHotkeyFilter = ...

        self.init_ui()
        self.init_hotkeys()

    def init_hotkeys(self):
        app = QApplication.instance()
        # F2 = 批量改价（再次按 F2 中断）
        self._hotkey_f2 = GlobalHotkeyFilter(self.model.toggle_batch_repricing, hotkey_id=3)
        # F3 = 采集（按 GUI 当前模式：通货模板 或 切换币种坐标）
        self._hotkey_f3 = GlobalHotkeyFilter(self.tab_store_manager.on_capture, hotkey_id=1)
        # F4 = 修改鼠标指向的道具
        self._hotkey_f4 = GlobalHotkeyFilter(self.model.reduce_price_of_hovered_item, hotkey_id=2)

        if self._hotkey_f2.register(VK_F2):
            app.installNativeEventFilter(self._hotkey_f2)
        else:
            self.model.add_status('全局热键 F2 注册失败，可能已被占用')

        if self._hotkey_f3.register(VK_F3):
            app.installNativeEventFilter(self._hotkey_f3)
        else:
            self.model.add_status('全局热键 F3 注册失败，可能已被占用')

        if self._hotkey_f4.register(VK_F4):
            app.installNativeEventFilter(self._hotkey_f4)
        else:
            self.model.add_status('全局热键 F4 注册失败，可能已被占用')

    def init_ui(self):
        self.setWindowTitle("摆摊管理")
        self.setGeometry(100, 100, 460, 640)

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        self.tab_store_manager = widgetStoreManager(self.model)
        self.setCentralWidget(self.tab_store_manager)

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
    watcher = AppStoreManager()
    watcher.show()

    sys.exit(app.exec())