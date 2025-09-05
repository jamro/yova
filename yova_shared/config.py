import os
import json

config_data = None

def reload_config():
    global config_data
    config_path = os.path.join(os.path.dirname(__file__), '..', 'yova.config.json')
    with open(config_path, 'r') as file:
        config_data = json.load(file)


def get_config(key_path: str = None):
    global config_data
    if config_data is None:
        reload_config()

    if key_path is None:
        return config_data

    path = key_path.split('.')
    pointer = config_data
    for key in path:
        if key in pointer:
            pointer = pointer[key]
        else:
            raise ValueError(f"Key {key_path} not found in config")
    
    return pointer