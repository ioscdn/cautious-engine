import os

from dotenv import dotenv_values


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

    def __repr__(self):
        return f"<Config {self.__config}>"

    def __str__(self):
        return str(self.__config)


class Config(ConfigParse):
    def __init__(
        self,
        config: str | dict = ".env",
        default: str | dict = {},
        override: bool = False,
    ):
        # generate __doc__
        """
        Config class for loading environment variables from a .env file or a dict.\n
        If a .env file is provided, it will be loaded and then the environment variables will be loaded.\n
        If a dict is provided, it will be loaded and then the environment variables will be loaded.\n
        If override is True, the environment variables will be loaded first and then the config will be loaded.

        Args:
            `config` (str, optional): Path to a .env file or a dict. Defaults to ".env".

            `default` (dict, optional): Path to a default .env file or a dict. Defaults to {}.

            `override` (bool, optional): Whether to override the environment variables with the config. Defaults to False.
        """
        __config = self.__load_config(default)
        __config.update(self.__load_config(config))

        if override:
            os.environ.update(__config)
        else:
            __config.update(os.environ)

        self.required = ConfigParse(__config, required=True)
        super().__init__(__config)

    def __load_config(self, config: dict | str) -> dict:
        if type(config) == dict:
            return config
        elif type(config) == str:
            config_path = os.path.abspath(config)
            if os.path.exists(config_path):
                return dotenv_values(config_path)
            else:
                raise FileNotFoundError(
                    f"Config file not found: {config_path}")  # fmt: skip
        else:
            raise TypeError(
                f"Config must be a dict or a path to a .env file, not {type(config)}")  # fmt: skip
