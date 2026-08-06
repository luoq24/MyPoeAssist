import re
import threading

import pythoncom

from PyQt6.QtCore import QObject, pyqtSignal

from models.currency_pricer import SUPPORTED_CURRENCIES, CurrencyPricer
from models.store_automation import StoreAutomation


# 价格行匹配：数字 + 通货名（中/英文）
_PATTERN_PRICE = re.compile(
    r'(\d+)\s*({})'.format('|'.join(re.escape(n) for n in list(SUPPORTED_CURRENCIES.keys()) + list(SUPPORTED_CURRENCIES.values()))),
    re.IGNORECASE,
)


class StoreManager(QObject):
    """
    摆摊管理：自动降价 / 后续自动上架。
    降价：解析鼠标指向道具的当前标价 -> 按折扣比例计算新价 -> 执行改价。
    """

    status_changed = pyqtSignal(str)
    prices_loaded = pyqtSignal()

    DISCOUNT_MIN = 10   # 最低降幅 %
    DISCOUNT_MAX = 50   # 最高降幅 %

    def __init__(self):
        super().__init__()

        self.pricer = CurrencyPricer()
        self._discount: int = 20  # 降幅百分比，默认 20%

        self.automation = StoreAutomation(chaos_value_fn=self.pricer.get_chaos_value)

        self._batch_cancel = threading.Event()
        self._batch_running = False
        self._batch_thread: threading.Thread | None = None

        self.load_prices()

    # ---------------- 价格表 ----------------
    def load_prices(self) -> bool:
        ok = self.pricer.load()
        if ok:
            self.add_status('价格表加载成功: {}'.format(self.pricer.price_path))
            self.prices_loaded.emit()
        else:
            self.add_status('价格表加载失败: {}'.format(self.pricer.price_path))
        return ok

    # ---------------- 折扣设置 ----------------
    def set_discount(self, percent: int):
        percent = max(self.DISCOUNT_MIN, min(self.DISCOUNT_MAX, int(percent)))
        self._discount = percent

    @property
    def discount(self) -> int:
        return self._discount

    # ---------------- 价格解析与计算 ----------------
    @staticmethod
    def parse_item_price(item_text: str) -> tuple[str | None, int | None]:
        """
        从道具文本中解析当前标价。
        返回 (通货中文名, 价格)。未匹配到返回 (None, None)。
        """
        if not item_text:
            return None, None
        for m in _PATTERN_PRICE.finditer(item_text):
            price = int(m.group(1))
            raw = m.group(2)
            # 中英文名统一为中文名
            name_cn = raw if raw in SUPPORTED_CURRENCIES else next(
                (k for k, v in SUPPORTED_CURRENCIES.items() if v.lower() == raw.lower()), None)
            if name_cn is None:
                continue
            return name_cn, price
        return None, None

    @staticmethod
    def calc_new_price(price: int, discount: int) -> int:
        """按降幅百分比计算新价，向下取整，最低为 1。"""
        discount = max(StoreManager.DISCOUNT_MIN, min(StoreManager.DISCOUNT_MAX, int(discount)))
        new_price = int(price * (100 - discount) / 100)
        return max(1, new_price)

    # ---------------- 自动降价（当前鼠标指向的 1 个道具）----------------
    def reduce_price_of_hovered_item(self):
        """F4 触发：在后台线程执行真实改价自动化，避免卡住 GUI。"""
        self.add_status('F4 触发单个改价...')
        self.automation._log_cb = self.add_status

        def _run():
            # 后台线程访问剪贴板/COM 前必须先初始化 COM，否则 OLE 报 CoInitialize 错误
            pythoncom.CoInitialize()
            try:
                self.automation.run_repricing(self._discount)
            finally:
                pythoncom.CoUninitialize()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ---------------- 批量改价（F2，可中断）----------------
    @property
    def batch_running(self) -> bool:
        return self._batch_running

    def toggle_batch_repricing(self):
        """F2 触发：未运行则开始批量改价，运行中则请求中断。"""
        if self._batch_running:
            self._batch_cancel.set()
            self.add_status('已发送中断请求，正在停止批量改价...')
            return

        self._batch_cancel.clear()
        self._batch_running = True
        self.automation._log_cb = self.add_status

        def _run():
            try:
                self.automation.run_batch_repricing(self._discount, is_cancelled=self._batch_cancel.is_set)
            finally:
                self._batch_running = False

        self._batch_thread = threading.Thread(target=_run, daemon=True)
        self._batch_thread.start()

    def toggle_batch_traversal(self):
        """F2 触发（调试）：未运行则开始遍历坐标测试，运行中则请求中断。"""
        if self._batch_running:
            self._batch_cancel.set()
            self.add_status('已发送中断请求，正在停止遍历测试...')
            return

        self._batch_cancel.clear()
        self._batch_running = True
        self.automation._log_cb = self.add_status

        def _run():
            try:
                self.automation.run_batch_traversal(is_cancelled=self._batch_cancel.is_set)
            finally:
                self._batch_running = False

        self._batch_thread = threading.Thread(target=_run, daemon=True)
        self._batch_thread.start()

    def capture_template(self, key: str):
        """把当前通货图标区域截图保存为指定通货的模板。"""
        try:
            self.automation._log_cb = self.add_status
            path = self.automation.capture_currency_template(key)
            self.add_status('已采集模板 {}: {}'.format(key, path))
        except Exception as e:
            self.add_status('模板采集失败: {}'.format(e))

    def capture_coordinate(self, slot: str):
        """采集当前鼠标位置作为切换币种坐标（归一化到第1档；slot: 'expand'、'put_on_shelf' 或通货中文名）。"""
        try:
            self.automation._log_cb = self.add_status
            if slot == 'put_on_shelf':
                delta_y = self.automation.capture_put_on_shelf_coordinate()
            else:
                delta_y = self.automation.capture_switch_coordinate(slot)
            self.add_status('已采集切换坐标 {}（当前档 delta_y={}）'.format(slot, delta_y))
        except Exception as e:
            self.add_status('坐标采集失败: {}'.format(e))

    # ---------------- 日志 ----------------
    def add_status(self, msg: str):
        self.status_changed.emit(str(msg))