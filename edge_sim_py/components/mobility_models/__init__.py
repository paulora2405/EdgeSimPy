"""Automatic Python configuration file."""

__version__ = "1.1.0"

# User mobility models
# ruff: noqa: F401
from .pathway import pathway
from .random_mobility import random_mobility
from .point_of_interest_mobility import point_of_interest_mobility
