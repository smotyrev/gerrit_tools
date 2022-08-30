import os
from pathlib import Path

config: dict = {}
_CONFIG_DIR = str(Path.home()) + os.sep + '.config' + os.sep + 'gerrit_tools'
_CONFIG_FILE = _CONFIG_DIR + os.sep + 'config'
if not os.path.isdir(_CONFIG_DIR):
    os.mkdir(_CONFIG_DIR)
if not os.path.isfile(_CONFIG_FILE):
    with open(_CONFIG_FILE, 'w+'):
        pass
with open(_CONFIG_FILE, 'r+') as rf:
    for line in rf.readlines():
        (k, v) = line.split('\t')
        config[k.strip()] = v.strip()


def save():
    with open(_CONFIG_FILE, 'w') as wf:
        for key in config:
            wf.write('{}\t{}\n'.format(key, config[key]))


def get_val(key: str):
    if key in config:
        return config[key]
    val = input('Enter value for {}: '.format(key))
    config[key] = val
    save()
    return val
