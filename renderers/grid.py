import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import jinja2
from datetime import datetime

from config.schema import SweepConfig

class GridRenderer:
    def __init__(self, output_dir: Path, config: SweepConfig):
        """
        Initialize the grid renderer.
        
        Args:
            output_dir: Base directory for the sweep
            config: Sweep configuration
        """
        self.output_dir = Path(output_dir)
        self.config = config
        
        # Get template directory
        template_dir = Path(__file__).parent / "templates"
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def _organize_grid_data(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organize results into a grid structure.
        
        Args:
            results: List of results
            
        Returns:
            Grid data structure
        """
        # Get grid axes from config - handle both Pydantic model and dict
        if hasattr(self.config.grid_axes, 'rows'):
            row_param = self.config.grid_axes.rows
            col_param = self.config.grid_axes.cols
        else:
            # Direct dictionary access
            row_param = self.config.grid_axes.get('rows', '')
            col_param = self.config.grid_axes.get('cols', '')
        
        # Collect unique values for rows and columns
        row_values = set()
        col_values = set()
        
        # Collect all parameters
        all_params = set()
        
        # Map for looking up results by their parameter values
        result_map = {}
        
        for result in results:
            params = result.get("params", {})
            if not params:
                continue
                
            # Add to all params
            for param in params:
                all_params.add(param)
                
            # Get row and column values
            row_value = params.get(row_param)
            col_value = params.get(col_param) if col_param else None
            
            if row_value is not None:
                row_values.add(row_value)
                
            if col_value is not None:
                col_values.add(col_value)
                
            # Create a key for this combination
            key = (row_value, col_value)
            result_map[key] = result
        
        # Sort the values
        sorted_row_values = sorted(row_values)
        sorted_col_values = sorted(col_values) if col_values else [None]
        
        # Create grid structure
        grid = []
        for row_value in sorted_row_values:
            row = []
            for col_value in sorted_col_values:
                key = (row_value, col_value)
                cell = result_map.get(key, {"status": "missing"})
                
                # Add row and column values to the cell
                cell_with_params = {
                    **cell,
                    "row_value": row_value,
                    "col_value": col_value
                }
                
                row.append(cell_with_params)
            grid.append(row)
            
        return {
            "grid": grid,
            "row_param": row_param,
            "col_param": col_param,
            "row_values": sorted_row_values,
            "col_values": sorted_col_values,
            "all_params": sorted(all_params)
        }
    
    def render_grid(self, results: List[Dict[str, Any]], output_path: Optional[Path] = None) -> Path:
        """
        Render results as an HTML grid.
        
        Args:
            results: List of results
            output_path: Custom output path (defaults to grid.html in the output directory)
            
        Returns:
            Path to the rendered HTML file
        """
        if output_path is None:
            output_path = self.output_dir / "grid.html"
            
        # Organize data for grid
        grid_data = self._organize_grid_data(results)
        
        # Add metadata - handle both Pydantic model and dict
        if hasattr(self.config.meta, 'copy'):
            meta = self.config.meta.copy()
        else:
            # Use model_dump if available, otherwise use dict
            try:
                meta = self.config.meta.model_dump()
            except AttributeError:
                # Fall back to dict for older versions
                try:
                    meta = self.config.meta.dict()
                except AttributeError:
                    # Direct dictionary if not a Pydantic model
                    meta = dict(self.config.meta)

        meta["rendered_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare template context
        context = {
            "meta": meta,
            "grid_data": grid_data,
            "base_url": ".",  # Relative paths
        }
        
        # Render the template
        template = self.env.get_template("grid.html.j2")
        html = template.render(**context)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(html)
            
        return output_path
