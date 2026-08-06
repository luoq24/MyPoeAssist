import os

import cv2
import numpy as np
from PIL import ImageGrab

# 摆摊可用的 5 种通货：key -> 中文名（用于模板目录命名与展示）
STORE_CURRENCIES = {
    'divine': '神圣石',
    'annulment': '剥离石',
    'chaos': '混沌石',
    'exalted': '崇高石',
    'alchemy': '点金石',
}

DEFAULT_TEMPLATE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'store_currency')
)


def capture_bbox(bbox: tuple[int, int, int, int]) -> np.ndarray | None:
    """截取指定屏幕区域 (x, y, x+w, y+h)，返回灰度 numpy 数组。"""
    try:
        img = ImageGrab.grab(bbox=bbox)
        return np.array(img.convert('L'))
    except Exception as e:
        print('capture_bbox 失败: {}'.format(e))
        return None


class CurrencyMatcher(object):
    """
    通货图标识别：截取固定区域 + 模板匹配（cv2.matchTemplate）。
    模板由用户自助采集，存放于 data/store_currency/<key>/ 下，每张为 png。
    """

    def __init__(self, template_dir: str = DEFAULT_TEMPLATE_DIR, threshold: float = 0.80):
        self._template_dir = template_dir
        self._threshold = threshold
        self._templates: dict[str, list[np.ndarray]] = {}
        self.load_templates()

    # ---------------- 模板管理 ----------------
    def load_templates(self):
        self._templates.clear()
        for key in STORE_CURRENCIES:
            path = self.template_dir_of(key)
            if not os.path.isdir(path):
                continue
            for f in sorted(os.listdir(path)):
                if not f.endswith('.png'):
                    continue
                img = cv2.imread(os.path.join(path, f), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self._templates.setdefault(key, []).append(img)

    def template_dir_of(self, key: str) -> str:
        return os.path.join(self._template_dir, key)

    def add_template(self, key: str, gray_img: np.ndarray) -> str:
        """把一张截图保存为该通货的模板，并加入内存。"""
        path = self.template_dir_of(key)
        os.makedirs(path, exist_ok=True)
        index = len(self._templates.get(key, [])) + 1
        fpath = os.path.join(path, 'tpl_{}.png'.format(index))
        cv2.imwrite(fpath, gray_img)
        self._templates.setdefault(key, []).append(gray_img)
        return fpath

    def count_templates(self) -> int:
        return sum(len(tpls) for tpls in self._templates.values())

    # ---------------- 识别 ----------------
    def detect(self, region: np.ndarray) -> str | None:
        key, _ = self.detect_with_score(region)
        return key

    def detect_with_score(self, region: np.ndarray) -> tuple[str | None, float]:
        """在给定区域中识别通货，返回 (key, 最高置信度)。"""
        key, score, _ = self.locate(region)
        return key, score

    def locate(self, region: np.ndarray) -> tuple[str | None, float, tuple[int, int]]:
        """
        在给定区域中定位最佳匹配的通货图标。
        返回 (key, 最大置信度, (图标中心 x, 图标中心 y))，其中坐标为区域内的局部坐标。
        未匹配到则 key=None、score 为最高值、坐标为 (0,0)。
        """
        if region is None or not self._templates:
            return None, -1.0, (0, 0)

        best_key = None
        best_score = -1.0
        best_center = (0, 0)
        for key, tpls in self._templates.items():
            for tpl in tpls:
                if tpl.shape[0] > region.shape[0] or tpl.shape[1] > region.shape[1]:
                    continue
                res = cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_key = key
                    # 图标中心 = 匹配框左上角 + 模板尺寸的一半
                    best_center = (max_loc[0] + tpl.shape[1] // 2, max_loc[1] + tpl.shape[0] // 2)

        if best_score >= self._threshold:
            return best_key, best_score, best_center
        return None, best_score, best_center