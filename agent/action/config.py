import sys

root_dir = __file__.rsplit("/", 3)[0]
if root_dir not in sys.path:
    sys.path.append(root_dir)


# Temporary directory to save generated and uploaded files
TEMP_DIR = f"{root_dir}/tmp/test"


def get_temp_dir():
    return TEMP_DIR


def set_temp_dir(temp_dir: str):
    global TEMP_DIR
    TEMP_DIR = temp_dir