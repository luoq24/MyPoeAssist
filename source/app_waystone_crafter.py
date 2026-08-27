import os
import sys
import time
import random
import threading
import ctypes
from ctypes import wintypes
from enum import Enum

import cv2
import numpy as np
import win32api
import win32con
import win32clipboard
import qdarktheme
from PIL import ImageGrab
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QMessageBox,
)

from models.bag import BagBase, ChestPoe2

PATH_ICON_APP = "data\\liemo.ico"


# ============================================================
# 常量
# ============================================================
# 全局热键 F2 / F3 / F4
VK_F2 = 0x71           # 虚拟键码：F2（开始/中断批量）
VK_F3 = 0x72           # 虚拟键码：F3（采集通货模板）
VK_F4 = 0x73           # 虚拟键码：F4（识别测试）
VK_SHIFT = 0x10        # 虚拟键码：Shift（按住可连续应用通货）
KEYEVENTF_KEYUP = 0x0002  # keybd_event 抬起标志

# 批量节奏（单位：秒，后续调试时按实际手感调整）
# 每个基础间隔都叠加一个随机抖动，使操作节奏更接近真人，降低规律性
DELAY_MOVE = 0.05        # 鼠标移动到格子中心后的停顿
DELAY_MOVE_JITTER = 0.03
DELAY_CLICK = 0.03       # 鼠标按下与抬起之间的停顿
DELAY_CLICK_JITTER = 0.02
DELAY_AFTER = 0.15       # 每次应用通货后的停顿
DELAY_AFTER_JITTER = 0.05
DELAY_CTRL_C = 0.05      # 按下 Ctrl+C 复制道具信息后、读取剪贴板前的等待
MIN_DELAY = 0.01         # 随机后的最小间隔下限

# 通货模板目录与识别参数
DIR_CURRENCY = os.path.join(os.path.dirname(__file__), "data", "currency")
CAPTURE_REGION_SIZE = 24    # 抓取光标附近区域的边长（像素）
CAPTURE_REGION_OFFSET = -13   # 抓取区域左上角相对光标的偏移（右下为正）
MATCH_THRESHOLD = 0.80      # 模板匹配最低置信度


# ============================================================
# 通货定义
# ============================================================
class EnumCurrency(Enum):
    """批量功能对应的改造通货。value 为中文名称。"""

    ALCHEMY = '点金石'    # 应用 1 次
    EXALTED = '崇高石'    # 应用 3 次
    VAAL = '瓦尔宝珠'     # 应用 1 次

    @property
    def key(self) -> str:
        """用于模板目录命名的英文键。"""
        return {
            EnumCurrency.ALCHEMY: 'alchemy',
            EnumCurrency.EXALTED: 'exalted',
            EnumCurrency.VAAL: 'vaal',
        }[self]

    @property
    def apply_count(self) -> int:
        return {
            EnumCurrency.ALCHEMY: 1,
            EnumCurrency.EXALTED: 3,
            EnumCurrency.VAAL: 1,
        }[self]

    @property
    def extra_interval(self) -> float:
        """每种通货在基础间隔之上额外追加的停顿（秒），用于放慢高价值通货节奏。"""
        return {
            EnumCurrency.ALCHEMY: 0.0,
            EnumCurrency.EXALTED: 0.0,
            EnumCurrency.VAAL: 0.3,
        }[self]


# ============================================================
# 全局键盘钩子（游戏前台时也能收到 F2/F3）
# ============================================================
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
HC_ACTION = 0


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulong),
    ]


class KeyboardHook(QObject):
    """低级键盘钩子：全局捕获指定按键，与前台窗口无关。

    在独立线程中安装 WH_KEYBOARD_LL 钩子并运行消息循环；
    通过在按下状态集合中记录 vkCode，抑制自动连发导致的重复触发。
    """

    key_pressed = pyqtSignal(int)  # 透传 vkCode

    HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._proc = None          # 持有回调引用，防止被 GC
        self._hook = None
        self._running = False
        self._down: set[int] = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        # 向钩子线程投递 WM_QUIT，唤醒其 GetMessageW 循环
        if self._thread is not None:
            tid = self._thread.native_id
            if tid:
                ctypes.windll.user32.PostThreadMessageW(tid, 0x0012, 0, 0)  # WM_QUIT

    def _run(self):
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        self._user32 = user32

        # 正确配置函数签名，避免 64 位指针被截断导致溢出
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = (
            ctypes.c_int, self.HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
        user32.CallNextHookEx.restype = ctypes.c_long
        user32.CallNextHookEx.argtypes = (
            ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        user32.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)

        self._proc = self.HOOKPROC(self._callback)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            print('SetWindowsHookExW 失败，全局热键不可用')
            self._running = False
            return

        msg = wintypes.MSG()
        while self._running:
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r <= 0:  # WM_QUIT 返回 0
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None

    def _callback(self, n_code, w_param, l_param):
        if n_code == HC_ACTION:
            kbd = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk = int(kbd.vkCode)
            if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # 集合里没有该键 → 是新按下；已存在 → 自动连发，忽略
                if vk not in self._down:
                    self._down.add(vk)
                    self.key_pressed.emit(vk)
            elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                self._down.discard(vk)
        return self._user32.CallNextHookEx(self._hook, n_code, w_param, l_param)


# ============================================================
# 通货检测器
# ============================================================
def is_admin() -> bool:
    """判断当前进程是否以管理员权限运行。"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def capture_cursor_region() -> np.ndarray | None:
    """抓取鼠标光标附近区域的图像，返回灰度 numpy 数组。

    在 POE2 中，右键拾取通货后，游戏会在光标附近渲染该通货图标，
    因此对光标附近区域截图即可拿到"当前拾取的通货"画面。
    """
    try:
        cx, cy = win32api.GetCursorPos()
    except Exception:
        return None

    x0 = cx + CAPTURE_REGION_OFFSET
    y0 = cy + CAPTURE_REGION_OFFSET
    bbox = (x0, y0, x0 + CAPTURE_REGION_SIZE, y0 + CAPTURE_REGION_SIZE)

    img = ImageGrab.grab(bbox=bbox)
    gray = np.array(img.convert('L'))
    return gray


class CurrencyDetector:
    """通过"光标附近截图 + 模板匹配"识别当前拾取的改造通货。

    模板由用户自助采集：在游戏中右键拾取某通货后，按下 F3，
    应用会把当前光标区域图像保存为该通货的模板，供后续匹配使用。
    """

    def __init__(self, template_dir: str = DIR_CURRENCY):
        self._template_dir = template_dir
        self._templates: dict[EnumCurrency, list[np.ndarray]] = {}
        self.load_templates()

    # ---------- 模板管理 ----------
    def load_templates(self):
        self._templates.clear()
        for currency in EnumCurrency:
            path = self.template_dir_of(currency)
            if not os.path.isdir(path):
                continue
            for f in os.listdir(path):
                if not f.endswith('.png'):
                    continue
                img = cv2.imread(os.path.join(path, f), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self._templates.setdefault(currency, []).append(img)

    def template_dir_of(self, currency: EnumCurrency) -> str:
        return os.path.join(self._template_dir, currency.key)

    def add_template(self, currency: EnumCurrency, gray_img: np.ndarray) -> str:
        """把一张截图保存为该通货的模板，并加入内存。"""
        path = self.template_dir_of(currency)
        os.makedirs(path, exist_ok=True)
        index = len(self._templates.get(currency, [])) + 1
        fpath = os.path.join(path, 'tpl_{}.png'.format(index))
        cv2.imwrite(fpath, gray_img)
        self._templates.setdefault(currency, []).append(gray_img)
        return fpath

    def count_templates(self) -> int:
        return sum(len(tpls) for tpls in self._templates.values())

    # ---------- 识别 ----------
    def detect(self) -> EnumCurrency | None:
        currency, _ = self.detect_with_score()
        return currency

    def detect_with_score(self) -> tuple[EnumCurrency | None, float]:
        """识别当前拾取的通货，返回 (通货, 最高置信度)。"""
        region = capture_cursor_region()
        if region is None or not self._templates:
            return None, -1.0
        return self.match(region)

    def match(self, region: np.ndarray) -> tuple[EnumCurrency | None, float]:
        if region is None or not self._templates:
            return None, -1.0

        best_currency = None
        best_score = -1.0

        for currency, tpls in self._templates.items():
            for tpl in tpls:
                if tpl.shape[0] > region.shape[0] or tpl.shape[1] > region.shape[1]:
                    continue
                res = cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_currency = currency

        if best_score >= MATCH_THRESHOLD:
            return best_currency, best_score
        return None, best_score


def _rand_sleep(base: float, jitter: float):
    """在基础间隔上叠加随机抖动后休眠，模拟真人操作节奏。"""
    delay = base + random.uniform(-jitter, jitter)
    if delay < MIN_DELAY:
        delay = MIN_DELAY
    time.sleep(delay)


def read_clipboard_text() -> str:
    """读取剪贴板文本（原生 win32clipboard，不依赖 Qt 的 OLE 剪贴板）。"""
    text = ''
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ''
    except Exception:
        pass
    finally:
        win32clipboard.CloseClipboard()
    return text


def count_affixes(item_text: str) -> tuple[int, int]:
    """统计道具文本中的前缀、后缀数量。返回 (前缀数, 后缀数)。"""
    prefix = item_text.count('前缀属性')
    suffix = item_text.count('后缀属性')
    return prefix, suffix


# ============================================================
# 批量加工执行器（后台线程运行，可中途取消）
# ============================================================
class WaystoneCrafter(QObject):
    _status_changed = pyqtSignal(str)
    _progress_changed = pyqtSignal(int, int)  # 当前格子序号, 总格子数
    _finished = pyqtSignal()

    def __init__(self, grid: BagBase):
        super().__init__()
        self._grid = grid
        self._cancel = False
        self._running = False
        self._thread: threading.Thread | None = None

    def is_running(self) -> bool:
        return self._running

    def start(self, currency: EnumCurrency):
        if self._running:
            return
        self._cancel = False
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(currency,), daemon=True)
        self._thread.start()

    def cancel(self):
        """请求中断，后台线程会在下一次循环检查时退出。"""
        self._cancel = True

    def connect_signals(self, on_status, on_progress, on_finished):
        self._status_changed.connect(on_status)
        self._progress_changed.connect(on_progress)
        self._finished.connect(on_finished)

    def _run(self, currency: EnumCurrency):
        try:
            self._apply_all(currency)
        finally:
            self._running = False
            self._finished.emit()

    def _iter_cells_from_cursor(self):
        """从鼠标当前位置所在格开始，向后遍历到网格结尾（不绕回）。列优先（先向下后向右），返回 (col,row) 生成器。

        用于"从半路开始批量"：批量中断后，只需把鼠标移到上次中断的格子上再按 F2 即可续批。
        """
        import win32api
        mx, my = win32api.GetCursorPos()
        start = self._grid.cell_index_at(mx, my)
        if start is None:
            self._status_changed.emit('鼠标在仓库外，从第 1 格开始批量')
            start_col, start_row = 0, 0
        else:
            start_col, start_row = start
            self._status_changed.emit('从鼠标所在格 ({},{}) 开始批量'.format(start_col, start_row))

        rows = self._grid._y_size
        total = self._grid._x_size * rows
        # 列优先线性序：idx = col*rows + row
        start_idx = start_col * rows + start_row
        for idx in range(start_idx, total):
            yield idx // rows, idx % rows

    def _apply_all(self, currency: EnumCurrency):
        total = self._grid._x_size * self._grid._y_size
        index = 0

        self._status_changed.emit(f'开始批量：{currency.value}')

        # 全程按住 Shift，保持"拾取通货"状态；结束或取消时再松开
        self._press_shift()
        try:
            # 列优先：从鼠标所在格开始（可从半路续批），先向下后向右
            for col, row in self._iter_cells_from_cursor():
                if self._cancel:
                    self._status_changed.emit('已取消批量功能')
                    return

                index += 1
                self._progress_changed.emit(index, total)

                x, y = self._grid.get_cell_center(col, row)

                # 移到格子并 Ctrl+C 读取道具信息，返回本格应应用通货的次数（0 表示跳过）
                apply_count = self._analyze_and_prepare(col, row, x, y, currency)
                if apply_count <= 0:
                    continue

                # 应用通货 apply_count 次
                for _ in range(apply_count):
                    if self._cancel:
                        self._status_changed.emit('已取消批量功能')
                        return
                    self._click_apply(currency)
        finally:
            self._release_shift()

        self._status_changed.emit('批量完成')

    def _analyze_and_prepare(self, col, row, x, y, currency: EnumCurrency) -> int:
        """移到格子中心，返回本格应应用通货的次数（0 表示跳过）。

        瓦尔宝珠不做剪贴板分析，直接应用，加快速度；其余通货用 Ctrl+C
        复制道具信息判断空格子/已腐化/词缀数量。
        """
        win32api.SetCursorPos((x, y))
        _rand_sleep(DELAY_MOVE, DELAY_MOVE_JITTER)

        # 瓦尔宝珠：无需 Ctrl+C，直接应用
        if currency is EnumCurrency.VAAL:
            return currency.apply_count

        # 复制前的剪贴板内容，用于判断空格子（Ctrl+C 不会改变空格子的剪贴板）
        before = read_clipboard_text()
        self._ctrl_c()
        time.sleep(DELAY_CTRL_C)
        item_text = read_clipboard_text()

        # 1. 空格子：剪贴板无变化
        if item_text == before:
            self._status_changed.emit('  ({},{}) 空格子，跳过'.format(x, y))
            return 0

        # 2. 已腐化：无法使用改造通货
        if '被腐化' in item_text:
            self._status_changed.emit('  已腐化的引路石，跳过')
            return 0

        # 3/4. 按通货计算应用次数
        prefix_count, suffix_count = count_affixes(item_text)
        affix_count = prefix_count + suffix_count

        if currency is EnumCurrency.ALCHEMY:
            # 词缀数量 >= 3 时已有稀有前缀/后缀，无法使用点金石
            if affix_count >= 3:
                self._status_changed.emit('  词缀数量 {} >= 3，无法使用点金石，跳过'.format(affix_count))
                return 0
            return currency.apply_count

        if currency is EnumCurrency.EXALTED:
            # 崇高石：可用次数 = 6 - 已有词缀数量
            count = 6 - affix_count
            if count <= 0:
                self._status_changed.emit('  词缀已满（{} 条），无法使用崇高石，跳过'.format(affix_count))
                return 0
            self._status_changed.emit(
                '  [崇高石] 格子({},{}) 已腐化=否 原词缀数={} 应使用崇高石={} 次'
                .format(col, row, affix_count, count))
            return count

        return currency.apply_count

    def _ctrl_c(self):
        """快速 Ctrl+C（无额外休眠，速度由 DELAY_CTRL_C 控制）。"""
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord('C'), 0, 0, 0)
        win32api.keybd_event(ord('C'), 0, KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def _press_shift(self):
        win32api.keybd_event(VK_SHIFT, 0, 0, 0)
        _rand_sleep(DELAY_CLICK, DELAY_CLICK_JITTER)

    def _release_shift(self):
        win32api.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        _rand_sleep(DELAY_CLICK, DELAY_CLICK_JITTER)

    def _click_apply(self, currency: EnumCurrency):
        """在当前光标位置左键点击应用通货（Shift 由 _apply_all 全程按住）。"""
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        _rand_sleep(DELAY_CLICK, DELAY_CLICK_JITTER)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        _rand_sleep(DELAY_AFTER + currency.extra_interval, DELAY_AFTER_JITTER)


# ============================================================
# 主窗口
# ============================================================
class AppWaystoneCrafter(QMainWindow):

    def __init__(self):
        super().__init__()

        # 仓库网格：地图仓库页，12x12，全部为引路石
        self.grid = ChestPoe2()

        self.crafter = WaystoneCrafter(self.grid)
        self.detector = CurrencyDetector()
        self.key_hook = KeyboardHook(self)
        self.key_hook.key_pressed.connect(self.on_key_pressed)

        # UI 控件引用
        self.label_progress: QLabel = ...
        self.text_log: QPlainTextEdit = ...
        self.combo_currency: QComboBox = ...
        self.btn_toggle: QPushButton = ...
        self.btn_capture: QPushButton = ...
        self.btn_reload: QPushButton = ...

        self.init_ui()
        self.connect_signals()
        self.key_hook.start()
        self.log('全局热键已启动：F3 采集模板，F2 开始/中断批量')
        self.log('当前已加载 {} 张通货模板'.format(self.detector.count_templates()))
        if not is_admin():
            self.log('提示：本应用未以管理员运行。若游戏以管理员权限运行，'
                     '游戏前台时全局热键将无法生效，请右键本应用"以管理员身份运行"。')

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle('引路石批量制作')
        self.setGeometry(100, 100, 420, 560)

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 操作说明
        tip = QLabel(
            '【操作流程】\n'
            '1. 进入游戏，打开仓库并定位到"地图仓库页"（全部道具为引路石）\n'
            '2. 右键点击背包中的改造通货（如点金石），使鼠标拾取该通货\n'
            '3. 按 F2 开始对应通货的【批量功能】\n'
            '4. 批量过程中再次按 F2 可中断；中断后把鼠标移到上次中断的格子上再按 F2，即可从半路继续批量\n'
            '5. 批量会自动跳过：空格子、已腐化的引路石；点金石会跳过词缀数量 >= 3 的引路石，崇高石则按\n'
            '   "6 - 已有词缀数量"自动计算应用次数\n\n'
            '【自动识别通货】\n'
            '1. 在下方"通货选择"中指定要采集的通货\n'
            '2. 游戏中右键拾取该通货后，按 F3 采集模板（每种建议采集 3~5 张）\n'
            '3. 采集完成后将"通货选择"设为"（自动检测拾取的通货）"，按 F2 即自动识别\n'
        )
        layout.addWidget(tip)

        # 通货选择
        row_currency = QHBoxLayout()
        row_currency.addWidget(QLabel('通货选择：'))
        self.combo_currency = QComboBox()
        self.combo_currency.addItem('（自动检测拾取的通货）', None)
        for currency in EnumCurrency:
            self.combo_currency.addItem(currency.value, currency)
        row_currency.addWidget(self.combo_currency, 1)
        layout.addLayout(row_currency)

        # 模板采集 / 重新加载
        row_template = QHBoxLayout()
        self.btn_capture = QPushButton('采集模板(F3)')
        self.btn_test_detect = QPushButton('识别测试(F4)')
        self.btn_reload = QPushButton('重新加载模板')
        row_template.addWidget(self.btn_capture)
        row_template.addWidget(self.btn_test_detect)
        row_template.addWidget(self.btn_reload)
        layout.addLayout(row_template)

        # 进度
        self.label_progress = QLabel('进度：未开始')
        layout.addWidget(self.label_progress)

        # 开始/取消按钮
        self.btn_toggle = QPushButton('开始批量')
        self.btn_toggle.setEnabled(False)
        layout.addWidget(self.btn_toggle)

        # 日志
        self.text_log = QPlainTextEdit()
        self.text_log.setReadOnly(True)
        layout.addWidget(self.text_log, 1)

    def connect_signals(self):
        self.btn_toggle.clicked.connect(self.on_btn_toggle)
        self.btn_capture.clicked.connect(self.on_capture_template)
        self.btn_test_detect.clicked.connect(self.on_test_detect)
        self.btn_reload.clicked.connect(self.on_reload_templates)
        self.crafter.connect_signals(
            on_status=self.on_status_changed,
            on_progress=self.on_progress_changed,
            on_finished=self.on_finished,
        )

    # ---------- 事件处理 ----------
    def on_key_pressed(self, vk_code: int):
        if vk_code == VK_F2:
            self.on_f2()
        elif vk_code == VK_F3:
            self.on_capture_template()
        elif vk_code == VK_F4:
            self.on_test_detect()

    def on_capture_template(self):
        if self.crafter.is_running():
            self.log('批量进行中，暂不能采集模板')
            return

        currency = self.combo_currency.currentData()
        if currency is None:
            self.log('请在"通货选择"下拉框中指定要采集的通货，再按 F3')
            return

        region = capture_cursor_region()
        if region is None:
            self.log('采集失败：无法获取光标附近区域截图')
            return

        path = self.detector.add_template(currency, region)
        self.log('已为 {} 采集模板：{}（共 {} 张）'.format(
            currency.value, os.path.basename(path), len(self.detector._templates[currency])))

    def on_reload_templates(self):
        self.detector.load_templates()
        self.log('模板已重新加载，共 {} 张'.format(self.detector.count_templates()))

    def on_test_detect(self):
        """识别测试：只截图+匹配，不执行批量，避免误耗通货。"""
        if self.crafter.is_running():
            self.log('批量进行中，暂不能识别测试')
            return

        currency, score = self.detector.detect_with_score()
        if currency is None:
            self.log('未识别到通货（最高置信度 {:.2f}，低于阈值 {}）'.format(score, MATCH_THRESHOLD))
        else:
            self.log('识别到通货：{}（置信度 {:.2f}）'.format(currency.value, score))

    def on_f2(self):
        if not self.isVisible():
            return

        # 运行中：再次按 F2 中断
        if self.crafter.is_running():
            self.crafter.cancel()
            self.log('已发送取消指令，正在停止批量功能...')
            return

        # 未运行：识别通货并开始批量
        currency = self._resolve_currency()
        if currency is None:
            self.log('未检测到拾取的改造通货，请先右键点击背包通货后再按 F2')
            return

        self.crafter.start(currency)

    def _resolve_currency(self) -> EnumCurrency | None:
        # 调试兜底：下拉框手动指定；否则自动检测当前拾取的通货
        selected = self.combo_currency.currentData()
        if selected is not None:
            return selected
        return self.detector.detect()

    def on_btn_toggle(self):
        if self.crafter.is_running():
            self.crafter.cancel()
        else:
            currency = self._resolve_currency()
            if currency is None:
                self.log('未选择通货，无法开始批量功能')
                return
            self.crafter.start(currency)

    # ---------- UI 回调 ----------
    def on_status_changed(self, text: str):
        self.log(text)

    def on_progress_changed(self, index: int, total: int):
        self.label_progress.setText(f'进度：{index} / {total}')

    def on_finished(self):
        self.btn_toggle.setText('开始批量')
        self.btn_toggle.setEnabled(False)
        self.label_progress.setText('进度：已结束')

    # ---------- 工具 ----------
    def log(self, text: str):
        self.text_log.appendPlainText(text)

    def closeEvent(self, event: QCloseEvent):
        if self.crafter.is_running():
            self.crafter.cancel()
        self.key_hook.stop()

        a = QMessageBox.question(
            self,
            '退出',
            '你确定要退出吗?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if a == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            self.key_hook.start()  # 继续使用
            event.ignore()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    app.setWindowIcon(QIcon(PATH_ICON_APP))
    watcher = AppWaystoneCrafter()
    watcher.show()

    sys.exit(app.exec())