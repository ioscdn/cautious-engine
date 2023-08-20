import os

from dotenv import load_dotenv


class ConfigParse:
    def __init__(
        self, config: dict, default_config: dict = None, required: bool = False
    ):
        self.__config = config
        self.__default_config = default_config or {}
        self.__required = required

    def __find_value(self, name: str):
        try:
            return self.__config.get(name) or self.__default_config[name]
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
        return name in self.config or name in self.default_config


class Config(ConfigParse):
    def __init__(self, config_path: str = ".env", default_values: dict = None):
        self.config_path = config_path
        self.default_values = default_values or {}
        self.load_config()
        self.required = ConfigParse(self.config, self.default_values, True)
        super().__init__(self.config, self.default_values)

    def load_config(self):
        load_dotenv(dotenv_path=self.config_path)
        self.config = os.environ
