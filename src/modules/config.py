import os

from dotenv import load_dotenv


class ConfigParse:
    def __init__(self, config: dict, required: bool = False):
        self.__config = config
        self.__required = required

    def __find_value(self, name: str):
        try:
            return self.__config[name]
        except KeyError:
            if self.__required:
                raise KeyError(
                        f"Missing required config value: {name}")  # fmt: skip
            else:
                return None

    def __get_parsed_value(self, name: str):
        value = self.__find_value(name)
        if type(value) == str and value.isdigit():
            return int(value)
        return value

    def __getattr__(self, name: str):
        return self.__get_parsed_value(name)

    def __getitem__(self, name: str):
        return self.__get_parsed_value(name)

    def __contains__(self, name: str):
        return name in self.config


class Config(ConfigParse):
    def __init__(self, config_path: str = ".env", default_values: dict = {}):
        config = self.load_config(config_path=config_path)
        config.update(default_values)
        self.required = ConfigParse(config, True)
        super().__init__(config)

    def load_config(self, config_path: str):
        load_dotenv(dotenv_path=config_path)
        return os.environ
