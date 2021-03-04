import yaml

def load_yaml(path: str):
    with open(path) as file:
        yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
    return yaml_dict