import ctypes
import time
import win32gui
from pywinauto import mouse

class MouseHelper(object):

    def __init__(self):
        pass
    
    @staticmethod
    def click_left():
        mouse_pos = win32gui.GetCursorPos()
        print('mmm->', mouse_pos)
        mouse.click(coords=mouse_pos)
        time.sleep(0.1)
