import re
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from tools.io_tool import IoTool


class ModCollector(QObject):
    str_mods_list_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()

        self._data: dict = None
        self._dict_prefix: dict = dict()
        self._dict_subfix: dict = dict()
        self._dict_newfix: dict = dict()
        self._dict_shenyuan: dict = dict()
        self._dict_bad: dict = dict()

        self._display_text: str = ''

        self.load_conf()
        
    def load_conf(self):
        try:
            data = IoTool.load_json('data\\mod\\map.json')
        except Exception as e:
            print(str(e))
            traceback.print_exc()
            return

        self._data = data
        self._dict_prefix = data['prefix']  # { 'fix1': 1, 'fix2a': 1, 'fix2b': 0 }
        self._dict_subfix = data['subfix']
        self._dict_newfix = data['newfix']
        self._dict_shenyuan = data['shenyuan']
        self._dict_bad = data['bad']

        self.clear_display()
        for mod, mod_val in self._dict_prefix.items():
            self.add_display('prefix-{} {}'.format(mod_val, mod))
        self.add_display('-' * 16)
        for mod, mod_val in self._dict_subfix.items():
            self.add_display('subfix-{} {}'.format(mod_val, mod))
        self.add_display('-' * 16)
        for mod, mod_val in self._dict_shenyuan.items():
            self.add_display('shenyuan-{} {}'.format(mod_val, mod))
        self.add_display('-' * 16)
        for mod, mod_val in self._dict_bad.items():
            self.add_display('bad-{} {}'.format(mod_val, mod))
        self.add_display('-' * 16)
        for mod, mod_val in self._dict_newfix.items():
            self.add_display('newfix-{} {}'.format(mod_val, mod))
        self.notify_display()

    def save_conf(self):

        if not self._data:
            # 不允许直接保存，这样安全些
            print('ModCollector._data 还没初始化')
            return

        self._data['newfix'] = self._dict_newfix

        IoTool.save_json(self._data, 'data\\mod\\map.json')

    def print_new(self):
        print('------- new mods: {} --------'.format(len(self._dict_newfix)))
        for mod in self._dict_newfix.keys():
            print(mod)

    @staticmethod
    def _replace_numbers(s: str) -> str:
        return re.sub(r'\d+', '#', s)
    
    @staticmethod
    def _str_mods_to_list(str_mods: str)-> list[str]:
        arr = str_mods.split('\n')
        return arr[:-1]  # 最后一个是空的

    def process_one_item_mods(self, str_mods: str):
        
        mods = self._str_mods_to_list(str_mods)

        for i in range(len(mods)):
            tp_mod = self._replace_numbers(mods[i])

            if self._dict_newfix.get(tp_mod) is None and \
                self._dict_prefix.get(tp_mod) is None and \
                self._dict_subfix.get(tp_mod) is None:
                
                self._dict_newfix[tp_mod] = 1

                # print(i, mods[i], '--->', tp_mod)
                self.add_display('newfix-{} {}'.format(1, tp_mod))
                self.notify_display()

    def clear_display(self):
        self._display_text = ''

    def add_display(self, single_line: str):
        self._display_text += '{}\n'.format(single_line)

    def notify_display(self):
        self.str_mods_list_changed.emit(self._display_text)

    def calc_count_prefix_subfix(self, str_mods: str):
        mods = self._str_mods_to_list(str_mods)

        unkown_mods = []
        count_prefix = 0
        count_subfix = 0
        count_shenyuan = 0
        count_bad = 0
        for mod in mods:
            tp_mod = self._replace_numbers(mod)
            
            # 深渊词缀，（与前后缀不冲突）
            n = self._dict_shenyuan.get(tp_mod)
            if n is not None:
                count_shenyuan += n

            # bad词缀，（与前后缀不冲突）
            n = self._dict_bad.get(tp_mod)
            if n is not None:
                count_bad += n

            n = self._dict_prefix.get(tp_mod)
            if n is not None:
                count_prefix += n
                continue

            n = self._dict_subfix.get(tp_mod)
            if n is not None:
                count_subfix += n
                continue
            
            # 不认识的词缀
            unkown_mods.append(tp_mod)

        if unkown_mods:
            print('unkonw mods: {}'.format(','.join(unkown_mods)))

        return count_prefix, count_subfix, count_shenyuan, count_bad, len(unkown_mods)            
