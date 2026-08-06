import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter


WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000

# 常用虚拟键码
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    """
    全局热键：基于 Windows RegisterHotKey，即使游戏窗口处于前台也能响应。
    需在 QApplication 上 installNativeEventFilter。
    每个实例绑定一个热键（hotkey_id 需唯一）。
    """

    def __init__(self, callback, hotkey_id: int = 1):
        super().__init__()
        self._callback = callback
        self._hotkey_id = hotkey_id
        self._registered = False

    def register(self, vk: int, modifiers: int = 0) -> bool:
        """注册全局热键。重复调用不会重复注册。"""
        if self._registered:
            return True
        ok = ctypes.windll.user32.RegisterHotKey(
            None, self._hotkey_id, modifiers | MOD_NOREPEAT, vk)
        self._registered = bool(ok)
        return self._registered

    def unregister(self):
        if self._registered:
            ctypes.windll.user32.UnregisterHotKey(None, self._hotkey_id)
            self._registered = False

    def nativeEventFilter(self, eventType, message):
        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
            self._callback()
            return True, 0
        return False, 0