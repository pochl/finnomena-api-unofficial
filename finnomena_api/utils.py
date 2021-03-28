import yaml
import re

def load_yaml(path: str):
    with open(path) as file:
        yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
    return yaml_dict

def remove_nonEng(string):
    string_list = string.split(' ')
    res = ' '.join([idx for idx in string_list if not re.findall("[^\u0000-\u05C0\u2100-\u214F]+", idx)])
    return res