import ctypes
import os, glob
import json
import copy


class IoTool(object):

    @staticmethod
    def get_files_from_dir(path_dir, full_path: bool=True, extd: tuple=('.png', '.jpg')) -> list[str]:
        images_path = []

        # 遍历，含：子文件夹
        for root, dirs, files in os.walk(path_dir):
            for file in files:
                file: str
                if file.endswith(extd):
                    if full_path:
                        images_path.append(os.path.join(root, file))
                    else:
                        images_path.append(file)
        return images_path

    @staticmethod
    def get_images_from_dir_specify(path_dir, specify_list: list[str], full_path: bool=True):
        images_path = []
        for root, dirs, files in os.walk(path_dir):
            for file in files:
                file: str
                if file.endswith('.png') or file.endswith('.jpg'):
                    name_pure = file[:-4]
                    if len(specify_list) == 0 or (name_pure in specify_list):
                        if full_path:
                            images_path.append(os.path.join(root, file))
                        else:
                            images_path.append(file)
        return images_path

    @staticmethod
    def clear_images_in_dir(path_dir):
        # 支持的图片文件扩展名
        image_extensions = ['*.jpg', '*.png']
        
        # 遍历所有指定扩展名的图片文件并删除
        for ext in image_extensions:
            image_files = glob.glob(os.path.join(path_dir, ext))  # 获取匹配的文件
            for image_file in image_files:
                try:
                    os.remove(image_file)  # 删除文件
                except Exception as e:
                    print(f"无法删除 {image_file}: {e}")

    @staticmethod
    def ensure_dir(path_dir: str):
        # 检查目录是否存在，如果不存在，则创建
        if not os.path.exists(path_dir):
            os.makedirs(path_dir)
   
    @staticmethod
    def load_json(path: str):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)

    @staticmethod
    def save_json(data, path: str):
        # 保存为 JSON 文件
        with open(path, "w", encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4)

    @staticmethod
    def is_local_path(path):
        if not isinstance(path, str):
            return False

        # 检查路径是否存在且是绝对路径
        if not os.path.isabs(path):
            return False
        
        # 检查驱动器是否存在
        drive = os.path.splitdrive(path)[0]
        if not drive:
            return False

        return True
    
    @staticmethod
    def fix_local_path(path_old: str)-> str:
        if len(path_old) < 4:
            return path_old
        
        # 首尾是双引号
        if path_old[0] == '\"' and path_old[-1] == '\"':
            return path_old[1:-1]

        # 开头是 "file:///"
        head_file = "file:///"
        if path_old.startswith(head_file):
            return path_old[len(head_file):]
        
        return path_old
