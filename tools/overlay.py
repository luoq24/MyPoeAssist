import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes


class TransparentOverlay:
    def __init__(self, target_title="Path of Exile"):
        self.target_title = target_title
        self.hwnd_target = win32gui.FindWindow(None, target_title)
        if not self.hwnd_target:
            raise Exception(f"未找到窗口: {target_title}")

        self.hwnd = None
        self.hdc = None
        self.mem_dc = None
        self.bitmap = None
        self.rects = []  # [(x, y, w, h)]

        self._create_overlay()

    # 定义必要的结构体
    class BLENDFUNCTION(ctypes.Structure):
        _fields_ = [
            ("BlendOp", wintypes.BYTE),
            ("BlendFlags", wintypes.BYTE),
            ("SourceConstantAlpha", wintypes.BYTE),
            ("AlphaFormat", wintypes.BYTE),
        ]

    def _create_overlay(self):
        wnd_class = win32gui.WNDCLASS()
        hinst = win32api.GetModuleHandle(None)
        wnd_class.hInstance = hinst
        wnd_class.lpszClassName = "OverlayWindow"
        wnd_class.lpfnWndProc = win32gui.DefWindowProc
        class_atom = win32gui.RegisterClass(wnd_class)

        # 获取目标窗口位置
        rect = win32gui.GetWindowRect(self.hwnd_target)
        x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]

        ex_style = (
            win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TOOLWINDOW
        )

        style = win32con.WS_POPUP

        # 创建窗口
        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            class_atom,
            None,
            style,
            x,
            y,
            w,
            h,
            None,
            None,
            hinst,
            None,
        )

        # 初始化DC
        self.hdc = win32gui.GetDC(self.hwnd)
        self.mem_dc = win32gui.CreateCompatibleDC(self.hdc)
        self.bitmap = win32gui.CreateCompatibleBitmap(self.hdc, w, h)
        win32gui.SelectObject(self.mem_dc, self.bitmap)

        # 置顶到目标窗口上层
        win32gui.SetWindowPos(
            self.hwnd,
            win32con.HWND_TOPMOST,  # 强制置顶，不再指定目标窗口
            x,
            y,
            w,
            h,
            win32con.SWP_SHOWWINDOW
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOMOVE,
        )

        self._clear()
        self._redraw()

    def _clear(self):
        """清空内存DC，保持透明"""
        rect = win32gui.GetClientRect(self.hwnd)
        w, h = rect[2], rect[3]
        # 使用 BLACKNESS 让整个 DC 透明
        win32gui.PatBlt(self.mem_dc, 0, 0, w, h, win32con.BLACKNESS)

    def _redraw(self):
        """重绘叠加层——用4条线画空心矩形"""
        rect = win32gui.GetClientRect(self.hwnd)
        w, h = rect[2], rect[3]

        # 清空内存DC，保持透明
        win32gui.PatBlt(self.mem_dc, 0, 0, w, h, win32con.BLACKNESS)

        # 创建红色画笔
        pen = win32gui.CreatePen(win32con.PS_SOLID, 2, win32api.RGB(255, 0, 0))
        old_pen = win32gui.SelectObject(self.mem_dc, pen)

        for (x, y, rw, rh) in self.rects:
            # 左上到右上
            win32gui.MoveToEx(self.mem_dc, x, y)
            win32gui.LineTo(self.mem_dc, x + rw, y)
            # 右上到右下
            win32gui.MoveToEx(self.mem_dc, x + rw, y)
            win32gui.LineTo(self.mem_dc, x + rw, y + rh)
            # 右下到左下
            win32gui.MoveToEx(self.mem_dc, x + rw, y + rh)
            win32gui.LineTo(self.mem_dc, x, y + rh)
            # 左下到左上
            win32gui.MoveToEx(self.mem_dc, x, y + rh)
            win32gui.LineTo(self.mem_dc, x, y)

        # 恢复原笔
        win32gui.SelectObject(self.mem_dc, old_pen)

        # 设置透明混合参数
        blend = (win32con.AC_SRC_OVER, 0, 255, win32con.AC_SRC_ALPHA)

        # 更新图层
        win32gui.UpdateLayeredWindow(
            self.hwnd,
            self.hdc,
            None,
            (w, h),
            self.mem_dc,
            (0, 0),
            0,
            blend,
            win32con.ULW_ALPHA,
        )

    def draw_rect(self, x, y, w, h):
        """绘制矩形框"""
        self.rects.append((x, y, w, h))
        self._redraw()

    def clear_rects(self):
        """清空矩形"""
        self.rects.clear()
        self._redraw()


if __name__ == "__main__":
    overlay = TransparentOverlay("流放之路：降临")  # 或者替换为中文名窗口
    overlay.draw_rect(100, 100, 200, 150)
    overlay.draw_rect(400, 300, 250, 180)

    import time
    time.sleep(2)
    overlay.clear_rects()

    input("按回车退出...")
    overlay.clear_rects()
