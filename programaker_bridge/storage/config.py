import json
import os

from xdg import XDG_CONFIG_HOME

BRIDGE_ENDPOINT_SUFFIX = "_bridge_endpoint"
AUTH_TOKEN_SUFFIX = "_authentication_token"

CONFIG_FILE_NAME = "config.json"


class Config:
    def __init__(self, name: str):
        name = name.lower()
        self.name = name
        self.directory = os.path.join(XDG_CONFIG_HOME, "programaker", "bridges", name)
        self.config_file_path = os.path.join(self.directory, CONFIG_FILE_NAME)

    def _get_config(self):
        if not os.path.exists(self.config_file_path):
            return {}
        with open(self.config_file_path, "rt") as f:
            return json.load(f)

    def _save_config(self, config):
        os.makedirs(self.directory, exist_ok=True)
        with open(self.config_file_path, "wt") as f:
            return json.dump(config, f)

    def get_bridge_endpoint(self):
        return self.get(
            value=self.name + BRIDGE_ENDPOINT_SUFFIX,
            prompt="Programaker bridge endpoint: ",
        )

    def get_auth_token(self):
        return self.get(
            value=self.name + AUTH_TOKEN_SUFFIX,
            prompt="Programaker authentication TOKEN: ",
        )

    def get(self, value, prompt):
        env_val = os.getenv(value.upper(), None)
        if env_val is not None:
            return env_val

        config = self._get_config()
        index = value.lower()
        if config.get(index, None) is None:
            config[index] = input(prompt)
            if not config[index]:
                raise Exception("No `{}` introduced".format(value))
            self._save_config(config)
        return config[index]
