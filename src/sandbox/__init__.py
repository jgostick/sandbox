import importlib.metadata as _metadata
import tomllib as _toml


try:
    __version__ = _metadata.version(__package__ or __name__)
except _metadata.PackageNotFoundError:
    with open("./pyproject.toml", "rb") as f:
        data = _toml.load(f)
        __version__ = data["project"]["version"]
    

from .main import *
