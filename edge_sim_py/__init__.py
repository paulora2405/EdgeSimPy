"""Automatic Python configuration file."""

__version__ = "1.1.0"


# Main simulation component
# ruff: noqa: F401, F403
from .simulator import Simulator

# Misc components
from .component_manager import ComponentManager

# EdgeSimPy components
from .components import *

# EdgeSimPy component builders
from .dataset_generator import *
