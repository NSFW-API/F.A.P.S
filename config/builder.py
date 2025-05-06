import itertools
import random
from typing import Dict, List, Any
import logging
import json

import numpy as np

from config.schema import SweepConfig, ParamValue, Range, RandomInt
# Use absolute imports
from helpers.hashing import hash_params

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('config.builder')


def _unwrap_nested_param(param: ParamValue) -> ParamValue:
    """
    Unwrap a potentially nested ParamValue object.

    Args:
        param: A potentially nested ParamValue object

    Returns:
        A non-nested ParamValue object
    """
    if hasattr(param, 'static') and isinstance(param.static, ParamValue):
        # We have a nested structure - use the inner ParamValue
        logger.info(f"Unwrapping nested ParamValue: {param}")
        return param.static
    return param


def _extract_primitive_value(param: ParamValue) -> Any:
    """
    Extract a primitive value from a ParamValue object.

    Args:
        param: A ParamValue object

    Returns:
        A primitive value
    """
    # First unwrap any nesting
    param = _unwrap_nested_param(param)

    if param.static is not None:
        return param.static

    if param.list is not None and len(param.list) > 0:
        return param.list[0]  # Return first value for primitive representation

    if param.range is not None:
        return param.range.start  # Return start value for primitive representation

    if param.random_int is not None:
        # Generate a random integer
        return random.randint(param.random_int.min, param.random_int.max)

    # Fallback
    return str(param)


def _resolve_param_value(param: ParamValue) -> List[Any]:
    """
    Resolve a ParamValue object to a list of concrete values.

    Args:
        param: A ParamValue object

    Returns:
        List of concrete parameter values
    """
    # First unwrap any nesting
    param = _unwrap_nested_param(param)

    logger.info(f"Resolving param type: {type(param)}")

    if param.static is not None:
        logger.info(f"Static param value: {param.static}")
        return [param.static]

    if param.list is not None:
        logger.info(f"List param values: {param.list}")
        return param.list

    if param.range is not None:
        # Use numpy to handle floating point ranges properly
        range_spec = param.range
        values = np.arange(
            range_spec.start,
            range_spec.end + range_spec.step / 2,  # Add half step to include end value
            range_spec.step
        )
        logger.info(f"Range values: {values.tolist()}")
        return values.tolist()

    if param.random_int is not None:
        # For random_int we just generate a single random integer
        rand_spec = param.random_int
        value = random.randint(rand_spec.min, rand_spec.max)
        logger.info(f"Random int value: {value}")
        return [value]

    # This should never happen due to validator
    logger.warning(f"Could not resolve parameter: {param}")
    return [str(param)]


def build_combinations(config: SweepConfig) -> List[Dict[str, Any]]:
    """
    Build all parameter combinations from a sweep configuration.

    Args:
        config: A validated SweepConfig object

    Returns:
        List of parameter combinations, each as a dictionary
    """
    logger.info("Building parameter combinations")

    # Debug the entire config structure
    logger.info(f"Config type: {type(config)}")
    try:
        # Use model_dump() instead of dict() for Pydantic v2 compatibility
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump()
        else:
            config_dict = config.dict()

        logger.info(f"Config structure sample: {str(config_dict)[:500]}...")

        # Log parameters structure
        for param_name, param_value in config.params.items():
            logger.info(f"Parameter {param_name} type: {type(param_value)}")
            # Try to dump parameter structure
            if hasattr(param_value, 'model_dump'):
                param_dict = param_value.model_dump()
            elif hasattr(param_value, 'dict'):
                param_dict = param_value.dict()
            else:
                param_dict = str(param_value)
            logger.info(f"Parameter {param_name} structure: {param_dict}")
    except Exception as e:
        logger.error(f"Error dumping config: {e}")

    param_values = {}
    static_params = {}

    # Separate static and varying parameters
    for param_name, param_spec in config.params.items():
        logger.info(f"Processing parameter: {param_name} (type: {type(param_spec)})")

        try:
            # Try to resolve the parameter value(s)
            values = _resolve_param_value(param_spec)
            logger.info(f"Parameter {param_name} resolved to {len(values)} values")

            if len(values) == 1:
                # Static parameter - store the actual primitive value
                static_params[param_name] = values[0]
                logger.info(f"Added as static parameter: {param_name} = {values[0]}")
            else:
                # Varying parameter - store the list of values
                param_values[param_name] = values
                logger.info(f"Added as varying parameter: {param_name} = {values}")

        except Exception as e:
            logger.error(f"Error processing parameter {param_name}: {e}")
            # In case of error, try to extract a primitive value
            try:
                primitive_value = _extract_primitive_value(param_spec)
                static_params[param_name] = primitive_value
                logger.warning(f"Extracted primitive value for {param_name}: {primitive_value}")
            except:
                # Last resort - convert to string
                static_params[param_name] = str(param_spec)
                logger.warning(f"Fallback: Added as string: {param_name} = {static_params[param_name]}")

    # If no varying parameters, return just the static parameters
    if not param_values:
        logger.warning("No varying parameters found! Creating single combination with only static parameters.")
        static_combo = {**static_params}

        # Generate hash for static combo
        try:
            hash_value = hash_params(static_combo)
            static_combo['_hash'] = hash_value
            logger.info(f"Generated hash for static combo: {hash_value}")
        except Exception as e:
            logger.error(f"Error generating hash: {e}")
            # Try again with string versions
            try:
                string_params = {k: str(v) for k, v in static_params.items()}
                hash_value = hash_params(string_params)
                static_combo['_hash'] = hash_value
                logger.info(f"Generated hash using string values: {hash_value}")
            except Exception as e2:
                logger.error(f"Error generating hash with strings: {e2}")
                static_combo['_hash'] = "error_generating_hash"

        return [static_combo]

    # Get the parameter names and corresponding value lists
    param_names = list(param_values.keys())
    value_lists = [param_values[name] for name in param_names]

    logger.info(f"Creating cartesian product of {len(param_names)} varying parameters")
    logger.info(f"Varying parameters: {param_names}")

    # Calculate total combinations
    total_combinations = 1
    for values in value_lists:
        total_combinations *= len(values)
    logger.info(f"Expecting {total_combinations} total combinations")

    # Generate all combinations
    combinations = []
    for value_combo in itertools.product(*value_lists):
        # Create a dictionary for this combination
        combo_dict = {**static_params}  # Start with static parameters

        # Add varying parameters for this combination
        for i, param_name in enumerate(param_names):
            combo_dict[param_name] = value_combo[i]

        # Log the current combination
        logger.info(f"Generated combination: {combo_dict}")

        # Add a hash for this combination
        try:
            combo_hash = hash_params(combo_dict)
            combo_dict['_hash'] = combo_hash
            logger.info(f"Hash for this combination: {combo_hash}")
        except Exception as e:
            logger.error(f"Error generating hash: {e}")
            combo_dict['_hash'] = "error_generating_hash"

        combinations.append(combo_dict)

    logger.info(f"Generated {len(combinations)} combinations in total")

    # Log first few combinations for debugging
    for i, combo in enumerate(combinations[:3]):
        logger.info(f"Sample combination {i+1}: {combo}")
        logger.info(f"Sample hash {i+1}: {combo.get('_hash', 'MISSING HASH!')}")

    return combinations


def get_param_metadata(config: SweepConfig) -> Dict[str, Dict[str, Any]]:
    """
    Get metadata about each parameter.

    Args:
        config: A validated SweepConfig object

    Returns:
        Dictionary mapping parameter names to their metadata
    """
    metadata = {}

    for param_name, param_spec in config.params.items():
        values = _resolve_param_value(param_spec)

        # Determine parameter type
        param_type = None

        if param_spec.static is not None:
            param_type = "static"
        elif param_spec.list is not None:
            param_type = "list"
        elif param_spec.range is not None:
            param_type = "range"
        elif param_spec.random_int is not None:
            param_type = "random_int"
        else:
            param_type = "unknown"

        metadata[param_name] = {
            "type": param_type,
            "is_static": len(values) == 1,
            "values": values
        }

    logger.info(f"Parameter metadata: {metadata}")
    return metadata