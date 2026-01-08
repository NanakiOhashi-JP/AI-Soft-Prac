import json
import os

def put_config(key, value):
    globals()[key] = value

def load_config():
    root = os.path.dirname(os.path.abspath(__file__))
    for path in ['config.json']:
        config_path = os.path.join(root, path)
        try:
            with open(config_path, 'rt') as f:
                d = json.load(f)
                for key, value in d.items():
                    put_config(key, value)
        except Exception as ex:
            print("WARN=", ex)
