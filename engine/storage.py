import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class LocalStorage:
    def __init__(self, base_dir: Path):
        """
        Initialize the local storage handler.
        
        Args:
            base_dir: Base directory for the sweep
        """
        self.base_dir = Path(base_dir)
        self.outputs_dir = self.base_dir / "outputs"
        self.log_file = self.base_dir / "sweep_log.jsonl"
        
        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save the configuration to a YAML file.
        
        Args:
            config: Configuration dictionary
        """
        config_path = self.base_dir / "cfg.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    def append_to_log(self, result: Dict[str, Any]) -> None:
        """
        Append a result to the log file.
        
        Args:
            result: Result metadata
        """
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(result) + '\n')
    
    def load_log(self) -> List[Dict[str, Any]]:
        """
        Load all results from the log file.
        
        Returns:
            List of result metadata
        """
        results = []
        
        if not self.log_file.exists():
            return results
        
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    results.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        return results
    
    def get_result_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """
        Find a result by its hash.
        
        Args:
            hash_value: Hash value to look for
            
        Returns:
            Result metadata or None if not found
        """
        output_dir = self.outputs_dir / hash_value
        params_path = output_dir / "params.json"
        
        if not params_path.exists():
            return None
        
        with open(params_path, 'r') as f:
            params = json.load(f)
        
        return {
            "hash": hash_value,
            "params": params,
            "output_path": str(output_dir / "output.png"),
            "thumb_path": str(output_dir / "thumb.jpg")
        }
    
    def get_successful_hashes(self) -> List[str]:
        """
        Get all hashes of successful jobs.
        
        Returns:
            List of hash values
        """
        successful_hashes = []
        
        for result in self.load_log():
            if result.get("status") == "succeeded" and "_hash" in result:
                successful_hashes.append(result["_hash"])
        
        return successful_hashes
