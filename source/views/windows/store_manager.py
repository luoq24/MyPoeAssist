from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QSlider, QSpinBox, QPushButton, QPlainTextEdit, QComboBox,
)

from models.store_manager import StoreManager
from tools.screen import STORE_CURRENCIES


class widgetStoreManager(QWidget):

    def __init__(self, model: StoreManager):
        super().__init__()

        self.model = model

        self.ui = None
        self._build_ui()
        self.connect_slots()
        self.refresh_prices()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # 折扣设置
        box_discount = QGroupBox('降价设置')
        form = QFormLayout(box_discount)

        h_discount = QHBoxLayout()
        self.slider_discount = QSlider(Qt.Orientation.Horizontal)
        self.slider_discount.setRange(StoreManager.DISCOUNT_MIN, StoreManager.DISCOUNT_MAX)
        self.slider_discount.setValue(self.model.discount)
        self.spin_discount = QSpinBox()
        self.spin_discount.setSuffix(' %')
        self.spin_discount.setRange(StoreManager.DISCOUNT_MIN, StoreManager.DISCOUNT_MAX)
        self.spin_discount.setValue(self.model.discount)
        h_discount.addWidget(self.slider_discount)
        h_discount.addWidget(self.spin_discount)
        form.addRow('降幅', h_discount)

        self.btn_reduce_one = QPushButton('修改鼠标指向的道具 [F4]')
        self.btn_reduce_one.setToolTip('全局快捷键 F4')
        form.addRow('', self.btn_reduce_one)

        self.btn_batch = QPushButton('遍历坐标测试 [F2]')
        self.btn_batch.setToolTip('全局快捷键 F2：遍历摊位网格开/关改价界面（调试坐标用），再次按 F2 中断')
        form.addRow('', self.btn_batch)
        root.addWidget(box_discount)

        # 采集设置（模板 / 切换坐标）
        box_tpl = QGroupBox('采集设置')
        box_tpl_layout = QVBoxLayout(box_tpl)

        # 第一行：采集模式 + 目标
        row_mode = QHBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItem('采集通货模板', 'template')
        self.combo_mode.addItem('采集切换坐标', 'coord')
        row_mode.addWidget(QLabel('模式'))
        row_mode.addWidget(self.combo_mode)

        self.combo_currency = QComboBox()
        for key, cn in STORE_CURRENCIES.items():
            self.combo_currency.addItem('{} ({})'.format(cn, key), key)

        self.combo_coord = QComboBox()
        self.combo_coord.addItem('展开下拉框', 'expand')
        for cn in STORE_CURRENCIES.values():
            self.combo_coord.addItem('选中 {}'.format(cn), cn)
        self.combo_coord.addItem('上架货物', 'put_on_shelf')

        row_mode.addWidget(self.combo_currency)
        row_mode.addWidget(self.combo_coord)
        box_tpl_layout.addLayout(row_mode)

        # 第二行：采集按钮
        row_btn = QHBoxLayout()
        self.btn_capture = QPushButton('采集当前位置 [F3]')
        self.btn_capture.setToolTip('全局快捷键 F3：按当前模式采集商品图标模板或切换币种坐标')
        row_btn.addWidget(self.btn_capture)
        box_tpl_layout.addLayout(row_btn)

        root.addWidget(box_tpl)

        # 价格参考
        box_price = QGroupBox('价格参考（通货）')
        box_price_layout = QVBoxLayout(box_price)
        self.label_prices = QLabel()
        self.label_prices.setWordWrap(True)
        box_price_layout.addWidget(self.label_prices)
        self.btn_reload = QPushButton('重新加载价格表')
        box_price_layout.addWidget(self.btn_reload)
        root.addWidget(box_price)

        # 状态日志
        box_status = QGroupBox('状态日志')
        box_status_layout = QVBoxLayout(box_status)
        self.text_status = QPlainTextEdit()
        self.text_status.setReadOnly(True)
        box_status_layout.addWidget(self.text_status)
        root.addWidget(box_status)

        root.addStretch()

    # ---------------- 信号 ----------------
    def connect_slots(self):
        self.slider_discount.valueChanged.connect(self.spin_discount.setValue)
        self.spin_discount.valueChanged.connect(self.slider_discount.setValue)
        self.spin_discount.valueChanged.connect(self.model.set_discount)

        self.btn_reduce_one.clicked.connect(self.model.reduce_price_of_hovered_item)
        self.btn_batch.clicked.connect(self.on_batch)
        self.btn_reload.clicked.connect(self.model.load_prices)
        self.btn_capture.clicked.connect(self.on_capture)
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)

        self.model.status_changed.connect(self.on_status_changed)
        self.model.prices_loaded.connect(self.refresh_prices)

        self.on_mode_changed()

    # ---------------- 响应 ----------------
    def on_status_changed(self, msg: str):
        self.text_status.appendPlainText(msg)

    def on_batch(self):
        self.model.toggle_batch_traversal()

    def on_mode_changed(self):
        # 模板模式显示币种下拉，坐标模式显示坐标槽位下拉
        is_template = self.combo_mode.currentData() == 'template'
        self.combo_currency.setVisible(is_template)
        self.combo_coord.setVisible(not is_template)

    def on_capture(self):
        if self.combo_mode.currentData() == 'template':
            key = self.combo_currency.currentData()
            if key:
                self.model.capture_template(key)
        else:
            slot = self.combo_coord.currentData()
            if slot:
                self.model.capture_coordinate(slot)

    def refresh_prices(self):
        self.label_prices.setText(self.model.pricer.format_reference_prices())