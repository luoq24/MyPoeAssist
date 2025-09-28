import win32gui
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from tools.soundPlayer import EnumShortSoundMap, SoundPlayer
from models.mod_collector import ModCollector


HWND_POE2_CLASSTYPE = 'POEWindowClass'
DELIMETER_ITEM_TEXT = '--------\n'


class Model(QObject):
    clipboard_changed = pyqtSignal(str)
    fenxi_result_notified = pyqtSignal(str)

    def __init__(self):

        super().__init__()

        self.soundPlayer = SoundPlayer(self)
        self.modCollector = ModCollector()

        self._enable_spy: bool = False
        self._enable_mod_collect: bool = False

        # 获取剪贴板对象
        self.clipboard = QApplication.clipboard()

        self.connect_slots()

    def connect_slots(self):
        pass

    def set_spy_enable(self, enable: bool):
        if enable:
            # 绑定信号：当剪贴板数据发生变化时触发
            self.clipboard.dataChanged.connect(self.on_clipboard_change)
        else:
            self.clipboard.dataChanged.disconnect(self.on_clipboard_change)

        self._enable_spy = enable

    def set_mod_collect_enable(self, enable: bool):
        self._enable_mod_collect = enable

    def on_clipboard_change(self):
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            if win32gui.GetClassName(hwnd) != HWND_POE2_CLASSTYPE:
                return
        else:
            return

        # 获取当前文本（如果不是文本，toText会返回空字符串）
        text = self.clipboard.text()

        if not text:
            return
        
        if not text.startswith('物品类别: 引路石\n'):
            return
        
        # 目前只处理引路石
        if not (text.startswith('物品类别: 引路石\n稀 有 度: 魔法\n') or text.startswith('物品类别: 引路石\n稀 有 度: 稀有\n')):
            return

        # 在这里写你要做的事情
        self.clipboard_changed.emit(text)
        # print("Clipboard changed:", len(text))

        str_mods = self.calc_mods_of_item(text)
        if self._enable_mod_collect:
            # 收集模式
            self.modCollector.process_one_item_mods(str_mods)
        else:
            # 常规模式
            count_prefix, count_subfix, count_shenyuan, count_bad, count_unknown = self.modCollector.calc_count_prefix_subfix(str_mods)

            self.play_notify_sound(count_prefix, count_subfix, count_shenyuan, count_bad, count_unknown)

            desc = '前缀数：{}， 后缀数：{}'.format(count_prefix, count_subfix)
            if count_unknown > 0:
                desc += '\n发现 {} 条未知词缀，详情看console'.format(count_unknown)
            self.fenxi_result_notified.emit(desc)


    def calc_mods_of_item(self, item_text: str):
        arr = item_text.split(DELIMETER_ITEM_TEXT)

        str_mods = arr[3]

        # print(str_mods)
        return str_mods
    
    def play_notify_sound(self, count_prefix, count_subfix, count_shenyuan, count_bad, count_unknown):
        sound = None
        total = count_prefix + count_subfix

        if count_unknown > 0:
            sound = EnumShortSoundMap.Unknown
        elif count_bad > 0:
            sound = EnumShortSoundMap.Bad
        elif count_shenyuan > 0:
            sound = EnumShortSoundMap.Shenyuan
        elif total == 0:
            sound = EnumShortSoundMap.Normal
        elif total <= 2:
            sound = EnumShortSoundMap.Magic
        elif total >= 6:
            # 词缀已满
            sound = EnumShortSoundMap.Full
        elif count_prefix >= 3:
            sound = EnumShortSoundMap.Bad3
        elif count_subfix == 3:
            if count_prefix == 0:
                sound = EnumShortSoundMap.Good3
            elif count_prefix == 1:
                sound = EnumShortSoundMap.Good4
            elif count_prefix == 2:
                sound = EnumShortSoundMap.Good5
        else:
            sound = EnumShortSoundMap.Wait

        if sound:
            self.soundPlayer.play(sound)
