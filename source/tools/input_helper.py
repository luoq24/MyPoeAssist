import time

import win32api
import win32con
import win32gui
from pywinauto import mouse


KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

# 数字键 0-9 的虚拟键码
_VK_DIGIT = {str(i): 0x30 + i for i in range(10)}


class MouseHelper(object):

    @staticmethod
    def click_left():
        pos = win32gui.GetCursorPos()
        mouse.click(coords=pos)
        time.sleep(0.1)

    @staticmethod
    def click_right():
        """在当前光标位置右键单击。"""
        x, y = win32gui.GetCursorPos()
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        time.sleep(0.1)

    @staticmethod
    def click_at_left(x, y, settle=0.0):
        """移动到 (x,y) 并左键单击。settle 为移动到位后、点击前的等待（游戏光标悬停稳定）。"""
        win32api.SetCursorPos((x, y))
        if settle > 0:
            time.sleep(settle)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.1)


class KeyboardHelper(object):

    @staticmethod
    def _press(vk: int, extended: bool = False):
        flags = KEYEVENTF_EXTENDEDKEY if extended else 0
        win32api.keybd_event(vk, 0, flags, 0)
        win32api.keybd_event(vk, 0, flags | KEYEVENTF_KEYUP, 0)

    @staticmethod
    def _chord(mod_vk: int, vk: int):
        win32api.keybd_event(mod_vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(mod_vk, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def ctrl_c():
        KeyboardHelper._chord(win32con.VK_CONTROL, ord('C'))
        time.sleep(0.1)

    @staticmethod
    def ctrl_a():
        KeyboardHelper._chord(win32con.VK_CONTROL, ord('A'))
        time.sleep(0.1)

    @staticmethod
    def esc():
        """按下并抬起 ESC 键（用于关闭价格调整界面）。"""
        KeyboardHelper._press(win32con.VK_ESCAPE)
        time.sleep(0.1)

    @staticmethod
    def type_digits(text: str):
        """输入一串纯数字（0-9）。"""
        for ch in text:
            vk = _VK_DIGIT.get(ch)
            if vk is None:
                continue
            KeyboardHelper._press(vk)
            time.sleep(0.01)