import logging
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field, validator, root_validator

# Set up logging
logger = logging.getLogger(__name__)


class RandomInt(BaseModel):
    min: int
    max: int

    # For JSON serialization, ensure the object has dict() and model_dump() methods
    if not hasattr(BaseModel, "model_dump"):
        def model_dump(self):
            return self.dict()


class Range(BaseModel):
    start: float
    end: float
    step: float

    @validator("step")
    def validate_step(cls, v, values):
        if "start" in values and "end" in values:
            if v <= 0:
                raise ValueError("Step must be positive")
            if (values["end"] - values["start"]) / v > 1000:
                raise ValueError("Range would produce too many values (>1000)")
        return v

    # For JSON serialization, ensure the object has dict() and model_dump() methods
    if not hasattr(BaseModel, "model_dump"):
        def model_dump(self):
            return self.dict()


class ParamValue(BaseModel):
    static: Optional[Any] = None
    list: Optional[List[Any]] = None
    range: Optional[Range] = None
    random_int: Optional[RandomInt] = None

    @root_validator(skip_on_failure=True)
    def check_one_field_set(cls, values):
        set_fields = sum(1 for f in ["static", "list", "range", "random_int"] if values.get(f) is not None)
        if set_fields != 1:
            raise ValueError("Exactly one of static, list, range, or random_int must be set")
        return values

    # For JSON serialization, ensure the object has dict() and model_dump() methods
    if not hasattr(BaseModel, "model_dump"):
        def model_dump(self):
            return self.dict()


class GridAxes(BaseModel):
    rows: str
    cols: str

    # For JSON serialization, ensure the object has dict() and model_dump() methods
    if not hasattr(BaseModel, "model_dump"):
        def model_dump(self):
            return self.dict()


class SweepConfig(BaseModel):
    meta: Dict[str, Any] = Field(...)
    params: Dict[str, Union[ParamValue, Any]] = Field(...)
    grid_axes: Optional[GridAxes] = None

    @validator("meta")
    def validate_meta(cls, v):
        required_fields = ["name", "base_model", "output_dir"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required meta field: {field}")
        return v

    @validator("params")
    def convert_params(cls, v):
        """Convert direct values to ParamValue objects with static field"""
        result = {}
        for key, value in v.items():
            # For debugging
            logger.info(f"Processing parameter {key}: {value}")

            if not isinstance(value, dict):
                # Direct value
                result[key] = ParamValue(static=value)
                logger.info(f"Direct value for {key}: {value}")

            elif "list" in value and value["list"] is not None:
                # List parameter
                result[key] = ParamValue(list=value["list"])
                logger.info(f"List parameter for {key}: {value['list']}")

            elif "range" in value and value["range"] is not None:
                # Range parameter
                range_spec = value["range"]
                # Ensure it's a proper Range object
                if isinstance(range_spec, dict):
                    range_obj = Range(**range_spec)
                else:
                    range_obj = range_spec
                result[key] = ParamValue(range=range_obj)
                logger.info(f"Range parameter for {key}: {range_obj}")

            elif "random_int" in value and value["random_int"] is not None:
                # Random int parameter
                rand_spec = value["random_int"]
                # Ensure it's a proper RandomInt object
                if isinstance(rand_spec, dict):
                    rand_obj = RandomInt(**rand_spec)
                else:
                    rand_obj = rand_spec
                result[key] = ParamValue(random_int=rand_obj)
                logger.info(f"Random int parameter for {key}: {rand_obj}")

            elif "static" in value:
                # Static parameter
                result[key] = ParamValue(static=value["static"])
                logger.info(f"Static parameter for {key}: {value['static']}")

            else:
                # Try to parse as ParamValue
                result[key] = ParamValue(**value)
                logger.info(f"Generic ParamValue for {key}: {value}")

        return result

    @validator("grid_axes", always=True)
    def set_default_grid_axes(cls, v, values):
        """If grid_axes not provided, use first two varying params"""
        if v is not None:
            return v

        if "params" not in values:
            return GridAxes(rows="", cols="")

        varying_params = [
            k for k, v in values["params"].items()
            if not (hasattr(v, "static") and v.static is not None)
        ]

        if len(varying_params) >= 2:
            return GridAxes(rows=varying_params[0], cols=varying_params[1])
        elif len(varying_params) == 1:
            return GridAxes(rows=varying_params[0], cols="")
        else:
            # Default to empty if no varying parameters
            return GridAxes(rows="", cols="")

    # For JSON serialization, ensure the object has dict() and model_dump() methods
    if not hasattr(BaseModel, "model_dump"):
        def model_dump(self):
            return self.dict()
