"""Indian personal-data detection benchmark and detector library."""

from importlib.metadata import version

from bharat_pii.labels import Label

__version__ = version("bharat-pii")

__all__ = ["Label", "__version__"]
