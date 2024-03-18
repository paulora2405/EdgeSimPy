"""Automatic Python configuration file."""

__version__ = "1.1.0"

# Network power models
# ruff: noqa: F401
from .network.conterato_network_power_model import ConteratoNetworkPowerModel

# Server power models
from .servers.cubic_server_power_model import CubicServerPowerModel
from .servers.linear_server_power_model import LinearServerPowerModel
from .servers.square_server_power_model import SquareServerPowerModel
