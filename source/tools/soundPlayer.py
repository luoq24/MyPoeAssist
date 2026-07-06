from enum import Enum
import os
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl, QObject


DIR_SOUND = os.path.join(os.path.dirname(__file__), os.pardir, "data", "audio")


class EnumShortSoundMap(Enum):
    Good3 = "3词好图"
    Good4 = "4词好图"
    Good5 = "5词好图"
    Bad3 = '3前缀坏图'
    Wait = '待培养地图'
    Magic = '魔法地图'
    Normal = '普通地图'
    Full = '满词缀地图'
    Unknown = '未知词缀'
    Shenyuan = '深渊地图'
    Bad = '讨厌词缀图'


class SoundPlayer(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._map_sound: dict[EnumShortSoundMap, QSoundEffect] = dict()

        self.load_all_sound()

    def load_all_sound(self):
        for eSound in EnumShortSoundMap:
            path = os.path.join(DIR_SOUND, '{}.wav'.format(eSound.value))
            sound_effect = QSoundEffect(self)
            if not os.path.exists(path):
                raise FileNotFoundError(f"提示音文件不存在: {path}")
            sound_effect.setSource(QUrl.fromLocalFile(path))
            sound_effect.setVolume(1.0)  # 0.0 ~ 1.0

            self._map_sound[eSound] = sound_effect

    def play(self, eSound: EnumShortSoundMap):
        sound_effect = self._map_sound.get(eSound)

        if sound_effect.isLoaded():
            sound_effect.play()
        else:
            print("提示音尚未加载完成。")

    def on_request_play_sound(self, eSound: EnumShortSoundMap):
        self.play(eSound)
