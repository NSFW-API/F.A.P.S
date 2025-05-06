"""
Configuration handling module
"""

# Don't import modules that import each other
from .schema import SweepConfig, ParamValue, Range, RandomInt, GridAxes

__all__ = [
    'SweepConfig', 'ParamValue', 'Range', 'RandomInt', 'GridAxes',
    'load_config', 'save_config',
    'build_combinations', 'get_param_metadata'
]

# Import these after defining __all__
from .loader import load_config, save_config
from .builder import build_combinations, get_param_metadata