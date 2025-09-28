import os
import os.path
import sys
import subprocess

# 指定只转这些ui
ONLY_LIST = []
# ONLY_LIST = ['item_helper']

_DIR_ROOT = os.path.dirname(__file__)
_DIR_ROOT = os.path.dirname(_DIR_ROOT)
_DIR_UI = os.path.join(_DIR_ROOT, 'data\\ui')
_DIR_UIPY = os.path.join(_DIR_ROOT, 'views\\uipy')


# 列出目录下的所有ui文件
def listUiFile():
    # UI文件所在的路径
    uis = []
    files = os.listdir(_DIR_UI)
    for filename in files:
        pure_name, ext = os.path.splitext(filename)

        if ext != '.ui':
            continue

        if len(ONLY_LIST) and (pure_name not in ONLY_LIST):            
            continue

        uis.append(filename)
    
    return uis


# 把后缀为ui的文件改成后缀为py的文件名
def transPyFile(filename):
    return os.path.splitext(filename)[0] + '.py'


# 调用系统命令把ui转换成py
def runMain():
    # 创建目录
    if not os.path.exists(_DIR_UIPY):
        os.makedirs(_DIR_UIPY)

    # 转换文件
    uis = listUiFile()
    for i in range(len(uis)):
        uiFile = uis[i]
        pyFile = transPyFile(uiFile)

        path_ui = os.path.join(_DIR_UI, uiFile)
        path_uipy = os.path.join(_DIR_UIPY, pyFile)
        subprocess.run([
            sys.executable, "-m", "PyQt6.uic.pyuic",
            path_ui,
            "-o",
            path_uipy,
        ], check=True)

        print('coverted {:02}: {}'.format(i + 1, path_uipy))


if __name__ == "__main__":
    runMain()
    sys.exit()
