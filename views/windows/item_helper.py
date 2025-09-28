import os
from PyQt6.QtWidgets import QWidget, QMessageBox, QStyle, QFrame, QSpacerItem, QSizePolicy, QSpinBox, QPushButton

from models.model import Model
from views.common.statusInfoMultiLine import StatusInfoMultiLine
from views.uipy.item_helper import Ui_Form


class widgetItenHelper(QWidget):

    def __init__(self, model: Model):
        super().__init__()

        self.model = model

        self._status_info: StatusInfoMultiLine = ...
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.init_layout()
        self.connect_slots()
    
    # region UI
    def init_layout(self):
        pass

    def connect_slots(self):
        self.model.clipboard_changed.connect(self.on_clipboard_changed)
        self.model.fenxi_result_notified.connect(self.on_fenxi_result_notified)

        self.ui.checkBox_spy_clipboard.toggled.connect(self.on_toggle_spy_clipboar)
        self.ui.checkBox_collect_mods.toggled.connect(self.on_toggle_mod_collect)

        self.ui.checkBox_spy_clipboard.setChecked(True)
        

    def on_clipboard_changed(self, text: str):
        self.ui.plainTextEdit_item_detail.setPlainText(text)

    def on_fenxi_result_notified(self, text: str):
        self.ui.textEdit_fenxi_result.setText(text)

    def on_toggle_spy_clipboar(self, checked: bool):
        self.model.set_spy_enable(checked)
        
    def on_toggle_mod_collect(self, checked: bool):
        self.model.set_mod_collect_enable(checked)
        