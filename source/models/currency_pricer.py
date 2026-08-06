import os
import traceback

from tools.io_tool import IoTool


# 摆摊调价/上架时，只允许使用的通货（中文名 -> 英文名）
SUPPORTED_CURRENCIES = {
    '神圣石': 'Divine Orb',
    '剥离石': 'Orb of Annulment',
    '混沌石': 'Chaos Orb',
    '崇高石': 'Exalted Orb',
    '点金石': 'Orb of Alchemy',
}

# 价格表默认路径（相对本文件: source/models -> 项目根 -> quick_currency_filter）
_DEFAULT_PRICE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'quick_currency_filter', 'poe2_currency_prices.json')
)


class CurrencyPricer(object):
    """
    通货价格参考
    负责加载 poe2_currency_prices.json，并为支持的通货提供价格查询。
    """

    def __init__(self, price_path: str = None):
        self._price_path = price_path or _DEFAULT_PRICE_PATH
        self._currencies: list[dict] = []
        self._meta: dict = {}
        self._loaded: bool = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def price_path(self) -> str:
        return self._price_path

    @property
    def meta(self) -> dict:
        return self._meta

    def load(self) -> bool:
        """加载价格表。成功返回 True，失败返回 False 并打印异常。"""
        try:
            data = IoTool.load_json(self._price_path)
            self._meta = data.get('meta', {})
            self._currencies = data.get('currencies', [])
            self._loaded = True
            return True
        except Exception as e:
            print('CurrencyPricer.load 失败: {}'.format(e))
            traceback.print_exc()
            self._loaded = False
            return False

    def get_currency(self, name_cn: str) -> dict | None:
        """按中文名查询单个通货条目，未找到返回 None。"""
        if not self._loaded:
            return None
        for c in self._currencies:
            if c.get('name') == name_cn:
                return c
        return None

    def get_chaos_value(self, name_cn: str) -> float | None:
        """返回指定通货的混沌石等价价格，未找到返回 None。"""
        c = self.get_currency(name_cn)
        if c is None:
            return None
        return c.get('chaosValue')

    def get_reference_prices(self) -> list[dict]:
        """
        返回支持的通货价格参考列表（按混沌石价格降序）。
        每项: {'name', 'name_en', 'chaosValue', 'divineValue', 'count'}
        """
        if not self._loaded:
            return []
        result = []
        for name_cn in SUPPORTED_CURRENCIES:
            c = self.get_currency(name_cn)
            result.append({
                'name': name_cn,
                'name_en': SUPPORTED_CURRENCIES[name_cn],
                'chaosValue': c.get('chaosValue') if c else None,
                'divineValue': c.get('divineValue') if c else None,
                'count': c.get('count') if c else None,
            })
        result.sort(key=lambda x: (x['chaosValue'] is None, -x['chaosValue'] if x['chaosValue'] else 0))
        return result

    def format_reference_prices(self) -> str:
        """格式化价格参考，用于 GUI 展示。"""
        lines = []
        for r in self.get_reference_prices():
            chaos = '--' if r['chaosValue'] is None else '{:.4f}'.format(r['chaosValue'])
            lines.append('{:<4} {:>10} 混沌石'.format(r['name'], chaos))
        if not self._loaded:
            lines.append('(价格表未加载)')
        return '\n'.join(lines)