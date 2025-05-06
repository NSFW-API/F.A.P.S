import os
import json
import yaml
from pathlib import Path
from typing import Union, Dict, Any, Optional

from .schema import SweepConfig


def load_config(config_path: Union[str, Path]) -> SweepConfig:
    """
    Load and validate a configuration file from YAML or JSON.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Validated SweepConfig object
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValueError: If the config file format is not supported
        ValidationError: If the config file doesn't match the schema
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    extension = config_path.suffix.lower()
    
    try:
        if extension == '.yaml' or extension == '.yml':
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
        elif extension == '.json':
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {extension}")
    except Exception as e:
        raise ValueError(f"Failed to parse config file: {e}")
    
    # Validate using pydantic model
    try:
        config = SweepConfig(**config_dict)
        return config
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def save_config(config: SweepConfig, output_path: Union[str, Path]) -> None:
    """
    Save a config object to a YAML file.
    
    Args:
        config: The configuration object to save
        output_path: Path where the config will be saved
    """
    output_path = Path(output_path)
    
    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict
    config_dict = config.dict()
    
    # Save as YAML
    with open(output_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
