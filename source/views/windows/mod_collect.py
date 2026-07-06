import os
from PyQt6.QtWidgets import QWidget, QMessageBox, QStyle, QFrame, QSpacerItem, QSizePolicy, QSpinBox, QPushButton

from models.model import Model
from views.common.statusInfoMultiLine import StatusInfoMultiLine
from views.uipy.mod_collect import Ui_Form


class widgetModCollect(QWidget):

    def __init__(self, model: Model):
        super().__init__()

        self.model = model.modCollector

        self._status_info: StatusInfoMultiLine = ...
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.init_layout()
        self.connect_slots()
    
    # region UI
    def init_layout(self):
        pass

    def connect_slots(self):
        self.ui.pushButton_load_conf.clicked.connect(self.model.load_conf)
        self.ui.pushButton_save_conf.clicked.connect(self.model.save_conf)
        self.ui.pushButton_print_new.clicked.connect(self.model.print_new)

        self.model.str_mods_list_changed.connect(self.on_mods_list_changed)

    def on_mods_list_changed(self, text: str):
        self.ui.plainTextEdit_all_mods.setPlainText(text)
