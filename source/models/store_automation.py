import os
import re
import time

import win32clipboard

from models.currency_pricer import SUPPORTED_CURRENCIES
from models.bag import StallPoe2
from tools.input_helper import KeyboardHelper, MouseHelper
from tools.screen import STORE_CURRENCIES, CurrencyMatcher, capture_bbox

DEFAULT_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'store', 'config.json')
)

# 通货降级决策：精度损失上限（目标混沌等价 vs 实际标价的偏差占比）
PRECISION_MAX_LOSS = 0.10
# 单币种价格上限，避免数字过大
PRICE_MAX = 999


def read_clipboard_text() -> str:
    """读取剪贴板文本（原生 win32clipboard，不依赖 Qt 的 OLE 剪贴板）。"""
    text = ''
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ''
    except Exception as e:
        print('read_clipboard 失败: {}'.format(e))
    finally:
        win32clipboard.CloseClipboard()
    return text


def _parse_price_number(text: str) -> int | None:
    """从剪贴板文本中解析当前价格数字。优先整个数字，否则回退到行内数字。"""
    stripped = text.strip()
    if stripped.isdigit():
        return int(stripped)
    # 兜底：取第一个出现的数字
    import re
    m = re.search(r'\d+', stripped)
    return int(m.group()) if m else None


def calc_new_price(price: int, discount: int) -> int:
    """按降幅百分比计算新价，向下取整，最低为 1（discount 限制在 10~50）。"""
    discount = max(10, min(50, int(discount)))
    return max(1, int(price * (100 - discount) / 100))


def decide_price(current_price: int, current_currency: str, discount: int,
                 chaos_value_fn, max_loss: float = PRECISION_MAX_LOSS):
    """
    按降幅计算新价，并在精度损失超过上限时做通货降级。

    思路：目标混沌等价 = 当前价 * 当前币种单价 * (1 - 降幅)。
    从当前币种向更便宜的通货依次尝试，取第一个精度损失 <= max_loss 的
    (价格, 币种)；若无满足项，则返回全部分案中损失最小的一个。

    返回 (new_price, target_currency)。
    """
    v0 = chaos_value_fn(current_currency)
    if not v0:
        # 当前币种价格未知，无法换算，退回简单降价（保持币种）
        return calc_new_price(current_price, discount), current_currency

    target_chaos = current_price * v0 * (1 - discount / 100)

    # 按单价从高到低排列，取当前币种及其之后（更便宜）的通货作为降级候选
    order = sorted(SUPPORTED_CURRENCIES, key=lambda c: (chaos_value_fn(c) is None, -chaos_value_fn(c)))
    cur_idx = order.index(current_currency) if current_currency in order else len(order) - 1
    candidates = order[cur_idx:]

    best = None
    best_loss = float('inf')
    for cn in candidates:
        v = chaos_value_fn(cn)
        if not v or v <= 0:
            continue
        rounded = int(round(target_chaos / v))
        rounded = max(1, min(PRICE_MAX, rounded))
        actual = rounded * v
        loss = abs(actual - target_chaos) / target_chaos if target_chaos > 0 else 0.0
        if loss <= max_loss:
            return rounded, cn
        if loss < best_loss:
            best_loss = loss
            best = (rounded, cn)

    if best:
        return best
    return calc_new_price(current_price, discount), current_currency


class StoreAutomation(object):
    """
    单个改价自动化（F4 触发）。
    流程：右键 -> Ctrl+C 复制当前价格 -> 图像识别通货图标 -> 计算新价 -> 键入 -> (改币种) -> 上架货物(暂不实现)。
    """

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH, matcher: CurrencyMatcher = None,
                 chaos_value_fn=None):
        self._config_path = config_path
        self._matcher = matcher or CurrencyMatcher()
        self._chaos_value_fn = chaos_value_fn
        self._config = {}
        self._log_cb = None
        self._grid = StallPoe2()  # 摊位道具网格（坐标待实测微调）
        self._seen_items: set[str] = set()  # 批量时已处理的道具文本缓存（用于跳过多格道具/重复）

    # ---------------- 配置 ----------------
    def load_config(self) -> bool:
        from tools.io_tool import IoTool
        try:
            self._config = IoTool.load_json(self._config_path)
            return True
        except Exception as e:
            print('StoreAutomation.load_config 失败: {}'.format(e))
            return False

    def _ensure_config(self):
        """确保配置已加载（首次调用时加载）。返回是否成功。"""
        if self._config:
            return True
        return self.load_config()

    def _log(self, msg: str):
        print(msg)
        if self._log_cb:
            self._log_cb(msg)

    def _currency_region(self) -> tuple[int, int, int, int] | None:
        r = self._config.get('price_ui', {}).get('currency_region')
        if not r or not (r.get('w') and r.get('h')):
            return None
        return r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']

    # ---------------- 模板采集 ----------------
    def capture_currency_template(self, key: str) -> str:
        """截取当前通货图标区域，保存为指定通货的模板。返回保存路径。"""
        if not self._ensure_config():
            raise RuntimeError('配置加载失败: {}'.format(self._config_path))
        bbox = self._currency_region()
        if bbox is None:
            raise RuntimeError('未配置通货图标区域（config.json 的 price_ui.currency_region）')
        region = capture_bbox(bbox)
        if region is None:
            raise RuntimeError('截图失败')
        return self._matcher.add_template(key, region)

    def _detect_tier(self):
        """
        识别当前界面处于哪个高度档：遍历基准区域 + 各 delta_y 偏移区域，
        取模板匹配分数最高的档。
        返回 (key, score, delta_y)。识别失败 key=None。
        """
        base = self._config.get('price_ui', {}).get('currency_region')
        if not base or not (base.get('w') and base.get('h')):
            return None, -1.0, 0
        x, y, w, h = base['x'], base['y'], base['w'], base['h']
        raw_dys = self._config.get('price_ui', {}).get('delta_ys', [])
        offsets = [0] + [int(d) for d in raw_dys if isinstance(d, (int, float))]

        best_key, best_score, best_dy = None, -1.0, 0
        for dy in offsets:
            bbox = (x, y + dy, x + w, y + dy + h)
            region = capture_bbox(bbox)
            if region is None:
                continue
            key, score, _ = self._matcher.locate(region)
            if score > best_score:
                best_score = score
                best_dy = dy
                best_key = key
        return best_key, best_score, best_dy

    # ---------------- 切换坐标采集 ----------------
    def capture_switch_coordinate(self, slot: str) -> int:
        """
        采集当前鼠标位置作为"切换币种"的坐标，并归一化到第 1 档（减去当前档 delta_y）。
        slot: 'expand'（展开下拉框）或通货中文名（选中该通货）。
        返回当前档 delta_y。
        """
        if not self._ensure_config():
            raise RuntimeError('配置加载失败: {}'.format(self._config_path))

        key, score, delta_y = self._detect_tier()
        if key is None:
            raise RuntimeError('未识别到币种图标（置信度 {:.2f}），请先打开价格调整界面并采集模板'.format(score))

        import win32gui
        mx, my = win32gui.GetCursorPos()
        bx, by = mx, my - delta_y  # 归一化到第 1 档

        cs = self._config.setdefault('price_ui', {}).setdefault('currency_switch', {})
        if slot == 'expand':
            cs['expand'] = {'x': bx, 'y': by}
        else:
            cs.setdefault('select', {})[slot] = {'x': bx, 'y': by}

        from tools.io_tool import IoTool
        IoTool.save_json(self._config, self._config_path)
        return delta_y

    # ---------------- 上架货物坐标采集/点击 ----------------
    def capture_put_on_shelf_coordinate(self) -> int:
        """
        采集当前鼠标位置作为「上架货物」按钮坐标，归一化到第 1 档（减去当前档 delta_y）。
        返回当前档 delta_y。
        """
        if not self._ensure_config():
            raise RuntimeError('配置加载失败: {}'.format(self._config_path))

        key, score, delta_y = self._detect_tier()
        if key is None:
            raise RuntimeError('未识别到币种图标（置信度 {:.2f}），请先打开价格调整界面并采集模板'.format(score))

        import win32gui
        mx, my = win32gui.GetCursorPos()
        bx, by = mx, my - delta_y  # 归一化到第 1 档

        self._config.setdefault('price_ui', {})['put_on_shelf'] = {'x': bx, 'y': by}

        from tools.io_tool import IoTool
        IoTool.save_json(self._config, self._config_path)
        return delta_y

    def click_put_on_shelf(self, delta_y: int | None = None) -> bool:
        """点击「上架货物」按钮（第 1 档坐标 + 当前档 delta_y）。"""
        if delta_y is None:
            _, _, delta_y = self._detect_tier()

        pos = self._config.get('price_ui', {}).get('put_on_shelf')
        if not pos:
            self._log('未配置上架货物坐标，跳过（先采集 F3 坐标模式）')
            return False

        settle = self._config['delays'].get('after_move', 0.3)
        MouseHelper.click_at_left(pos['x'], pos['y'] + delta_y, settle=settle)
        time.sleep(self._config['delays'].get('after_put_on_shelf', 0.3))
        self._log('已点击「上架货物」')
        return True

    def switch_currency(self, target_cn: str, delta_y: int | None = None) -> bool:
        """执行币种切换：第一次单击展开下拉列表，第二次单击选中目标通货（坐标 = 第1档 + 当前档 delta_y）。"""
        if delta_y is None:
            _, _, delta_y = self._detect_tier()

        cs = self._config.get('price_ui', {}).get('currency_switch', {})
        expand = cs.get('expand')
        sel = (cs.get('select') or {}).get(target_cn)
        if not (expand and sel):
            self._log('未配置切换坐标（{}），跳过币种切换'.format(target_cn))
            return False

        delays = self._config['delays']
        # 展开后等待列表弹出，再点击选中（列表弹出需要时间，可单独调）
        delay_expand = delays.get('after_switch_expand', 0.5)
        delay_after = delays.get('after_switch', 0.3)
        # 每次移动到位后、点击前的等待（鼠标移动到目标需要时间，游戏需悬停稳定）
        settle = delays.get('after_move', 0.2)

        ex, ey = expand['x'], expand['y'] + delta_y
        sx, sy = sel['x'], sel['y'] + delta_y
        MouseHelper.click_at_left(ex, ey, settle=settle)
        time.sleep(delay_expand)
        MouseHelper.click_at_left(sx, sy, settle=settle)
        time.sleep(delay_after)
        self._log('已切换币种为 {}'.format(target_cn))
        return True

    # ---------------- 改价主流程 ----------------
    def run_repricing(self, discount: int):
        """单个改价（F4）：对鼠标当前指向的道具执行完整改价流程。"""
        self._log('----- 单个改价开始 -----')
        if not self.load_config():
            self._log('配置加载失败，终止')
            return
        self._repricing_once(discount)
        self._log('----- 单个改价完成 -----')

    def _iter_cells_from_cursor(self):
        """从鼠标当前位置所在格开始，向后遍历到摊位结尾（不绕回）。列优先（先向下后向右），返回 (col,row) 生成器。"""
        import win32api
        mx, my = win32api.GetCursorPos()
        start = self._grid.cell_index_at(mx, my)
        if start is None:
            self._log('鼠标在摊位外，从第 1 格开始遍历')
            start_col, start_row = 0, 0
        else:
            start_col, start_row = start
            self._log('鼠标在摊位内，从格 ({},{}) 开始向后遍历'.format(start_col, start_row))

        cols = self._grid._x_size
        rows = self._grid._y_size
        total = cols * rows
        # 列优先线性序：idx = col*rows + row
        start_idx = start_col * rows + start_row
        for idx in range(start_idx, total):
            yield idx // rows, idx % rows

    def run_batch_repricing(self, discount: int, is_cancelled=None):
        """批量改价（F2）：遍历摊位网格每个道具格，逐个执行改价流程。"""
        self._log('----- 批量改价开始 -----')
        if not self.load_config():
            self._log('配置加载失败，终止')
            return

        self._seen_items.clear()  # 每次批量新建缓存，避免跨轮误跳过

        index = 0
        # 从鼠标所在格开始（含回绕），列优先向后遍历
        for col, row in self._iter_cells_from_cursor():
            if is_cancelled and is_cancelled():
                self._log('已中断批量改价')
                return
            index += 1
            x, y = self._grid.get_cell_center(col, row)
            self._log('---- ({}/{}) 改价格 ({},{}) ----'.format(index, 144, col, row))

            # 先移动并 Ctrl+C 取道具文本，命中缓存则跳过多格道具的其它格子
            import win32api
            win32api.SetCursorPos((x, y))
            # 身份识别用更短悬停延迟（空格/已处理道具跳过时显著提速）
            time.sleep(self._config['delays'].get('after_move_ident', 0.1))
            KeyboardHelper.ctrl_c()
            time.sleep(self._config['delays'].get('after_ctrl_c', 0.2))
            item_text = read_clipboard_text().strip()
            if item_text and item_text in self._seen_items:
                self._log('     道具已处理过，跳过')
                continue
            if item_text:
                self._seen_items.add(item_text)

            # 光标已在格子中心，无需在 _repricing_once 内再次移动
            self._repricing_once(discount, pos=None)

        self._log('----- 批量改价完成 -----（处理 {} 个不同道具）-----'.format(len(self._seen_items)))

    def run_batch_traversal(self, is_cancelled=None):
        """批量遍历测试（调试用）：只移动+右键打开改价界面，等待后 ESC 关闭，不实际改价。"""
        self._log('----- 遍历坐标测试开始 -----')
        if not self.load_config():
            self._log('配置加载失败，终止')
            return

        import win32api
        self._seen_items.clear()  # 每次测试新建缓存，验证多格道具跳过
        index = 0

        # 从鼠标所在格开始（含回绕），列优先向后遍历
        for col, row in self._iter_cells_from_cursor():
            if is_cancelled and is_cancelled():
                self._log('已中断遍历测试')
                return
            index += 1
            x, y = self._grid.get_cell_center(col, row)
            self._log('---- ({}/{}) 格 ({},{}) 中心 ({},{}) ----'.format(index, 144, col, row, x, y))
            win32api.SetCursorPos((x, y))
            time.sleep(self._config['delays'].get('after_move', 0.3))

            # Ctrl+C 取道具文本，命中缓存则跳过多格道具的其它格子
            KeyboardHelper.ctrl_c()
            time.sleep(self._config['delays'].get('after_ctrl_c', 0.2))
            item_text = read_clipboard_text().strip()
            if item_text and item_text in self._seen_items:
                self._log('     道具已处理过，跳过')
                continue
            if item_text:
                self._seen_items.add(item_text)

            MouseHelper.click_right()
            time.sleep(self._config['delays'].get('after_right_click', 0.4))
            # 检测改价页是否打开：未打开说明空格/锁定，直接跳过
            key, score, _ = self._detect_tier()
            if key is None:
                self._log('     未打开改价页（空格/锁定），跳过')
                continue
            self._log('     改价页已打开，ESC 关闭')
            time.sleep(0.5)          # 等待改价界面稳定
            KeyboardHelper.esc()     # 关闭改价界面
            time.sleep(0.2)

        self._log('----- 遍历坐标测试完成 -----')

    def _repricing_once(self, discount: int, pos: tuple[int, int] | None = None):
        """
        对单个道具执行改价流程。
        pos：鼠标目标坐标（批量用）；None 表示使用当前鼠标位置（单个改价）。
        """
        # 诊断：确认实际加载的配置路径与通货区域
        self._log('config: {} -> currency_region: {}'.format(self._config_path, list(self._currency_region() or ())))

        if pos is not None:
            import win32api
            win32api.SetCursorPos(pos)
            time.sleep(self._config['delays'].get('after_move', 0.3))

        # 1. 右键：弹出价格调整界面
        MouseHelper.click_right()
        time.sleep(self._config['delays'].get('after_right_click', 0.4))

        # 1.1 先检测改价页是否打开：未打开说明空格/锁定，跳过（避免读到旧剪贴板）
        key, score, delta_y = self._detect_tier()
        if key is None:
            self._log('未打开改价页（空格/锁定），跳过')
            return
        currency_cn = STORE_CURRENCIES[key]
        self._log('识别币种: {} (score={:.2f}, delta_y={})'.format(currency_cn, score, delta_y))

        # 2. Ctrl+C：复制当前价格数字
        KeyboardHelper.ctrl_c()
        time.sleep(self._config['delays'].get('after_ctrl_c', 0.2))

        # 2.1 读取当前价格
        cur_price = _parse_price_number(read_clipboard_text())
        if cur_price is None:
            self._log('未解析到当前价格，可能道具处于锁定期')
            return
        self._log('当前标价: {}'.format(cur_price))

        # 4. 计算新价格（含通货降级优化）
        if self._chaos_value_fn:
            new_price, target_cn = decide_price(cur_price, currency_cn, discount, self._chaos_value_fn)
        else:
            new_price, target_cn = calc_new_price(cur_price, discount), currency_cn
        self._log('降幅 {}% -> 新价: {} {}'.format(discount, new_price, target_cn))
        if target_cn != currency_cn:
            self._log('通货降级: {} -> {}（精度损失控制在 {}% 内）'.format(
                currency_cn, target_cn, int(PRECISION_MAX_LOSS * 100)))

        # 5. 键入新价格（先全选覆盖旧数字）
        KeyboardHelper.ctrl_a()
        KeyboardHelper.type_digits(str(new_price))
        time.sleep(self._config['delays'].get('after_type', 0.2))

        # 6. 币种变化时切换下拉框（第1档坐标 + 当前档 delta_y）
        if target_cn != currency_cn:
            self.switch_currency(target_cn, delta_y=delta_y)

        # 7. 上架货物（第1档坐标 + 当前档 delta_y；未采集坐标则跳过）
        self.click_put_on_shelf(delta_y=delta_y)