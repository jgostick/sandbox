import tomllib as _toml


with open("./pyproject.toml", "rb") as f:
    data = _toml.load(f)
    __version__ = data["project"]["version"]
    

from .main import *
