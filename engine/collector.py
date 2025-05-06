import json
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import aiohttp

from helpers.image import create_thumbnail
from helpers.retry import async_retry


class ResultCollector:
    def __init__(
            self,
            output_dir: Path,
            overwrite: bool = False
    ):
        """
        Initialize the result collector.
        
        Args:
            output_dir: Base directory for storing results
            overwrite: Whether to overwrite existing results
        """
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
        self.log_file = self.output_dir / "sweep_log.jsonl"

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create outputs directory
        (self.output_dir / "outputs").mkdir(exist_ok=True)

        # Initialize session
        self.session = None

    async def __aenter__(self):
        """Set up async resources when entering context manager"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async resources when exiting context manager"""
        if self.session:
            await self.session.close()
            self.session = None

    def _get_hash_dir(self, hash_value: str) -> Path:
        """Get the directory for a specific hash"""
        return self.output_dir / "outputs" / hash_value

    def result_exists(self, hash_value: str) -> bool:
        """Check if a result already exists for this hash"""
        hash_dir = self._get_hash_dir(hash_value)
        return hash_dir.exists() and (hash_dir / "output.png").exists()

    @async_retry(retries=3, base_delay=1.0)
    async def download_file(self, url: str, output_path: Path) -> None:
        """
        Download a file from a URL.

        Args:
            url: URL to download from
            output_path: Path where the file will be saved
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Ensure output path is a Path object and its parent directory exists
        output_path = Path(str(output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert the URL to a string if it isn't already
        if not isinstance(url, str):
            url = str(url)

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                with open(output_path, 'wb') as f:
                    f.write(await response.read())
        except Exception as e:
            print(f"Error downloading file: {e}")
            # Re-raise the exception for the retry decorator to handle
            raise

    async def collect_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect a result from a completed job.

        Args:
            result: Job result including metadata

        Returns:
            Updated result metadata
        """
        if isinstance(result, Exception):
            # Handle failed jobs
            return {
                "status": "failed",
                "error": str(result),
                "timestamp": datetime.now().isoformat()
            }

        hash_value = result.get("_hash")
        if not hash_value:
            return {**result, "status": "failed", "error": "Missing hash value"}

        hash_dir = self._get_hash_dir(hash_value)

        # Check if result already exists and we're not overwriting
        if not self.overwrite and self.result_exists(hash_value):
            return {**result, "status": "skipped", "reason": "Already exists"}

        # Create hash directory
        hash_dir.mkdir(exist_ok=True)

        # Results that need to be saved
        output_path = hash_dir / "output.png"
        thumb_path = hash_dir / "thumb.jpg"
        params_path = hash_dir / "params.json"

        try:
            # Download result image
            if result.get("result_url"):
                await self.download_file(result["result_url"], output_path)

                # Create thumbnail
                create_thumbnail(output_path, thumb_path)

                # Prepare parameters for JSON serialization - handle non-serializable types
                serializable_params = {}
                for k, v in result.get("params", {}).items():
                    # Convert non-JSON serializable types to strings
                    if isinstance(v, (bytes, bytearray)):
                        serializable_params[k] = v.decode('utf-8', errors='replace')
                    elif hasattr(v, '__dict__'):  # Handle custom objects
                        serializable_params[k] = str(v)
                    else:
                        serializable_params[k] = v

                # Save parameters
                with open(params_path, 'w') as f:
                    json.dump(serializable_params, f, indent=2, default=str)

                # Prepare a serializable result for appending to log file
                serializable_result = result.copy()
                serializable_result["params"] = serializable_params

                # Remove potentially non-serializable fields like FileOutput objects
                # If result_url exists, we don't need to store the actual output object
                if "output" in serializable_result:
                    serializable_result["output"] = str(serializable_result["output"])

                # Append to log file
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(serializable_result, default=str) + '\n')

                return {**result, "output_path": str(output_path), "thumb_path": str(thumb_path)}
            else:
                return {**result, "status": "failed", "error": "No result URL"}
        except Exception as e:
            print(f"Error collecting result: {e}")
            import traceback
            print(traceback.format_exc())
            return {**result, "status": "failed", "error": str(e)}

    async def collect_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Collect multiple results in parallel.
        
        Args:
            results: List of job results
            
        Returns:
            List of updated results
        """
        tasks = [self.collect_result(result) for result in results]
        return await asyncio.gather(*tasks)

    def load_previous_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Load previous results from the log file.
        
        Returns:
            Dictionary mapping hash values to result metadata
        """
        results = {}

        if not self.log_file.exists():
            return results

        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    result = json.loads(line.strip())
                    hash_value = result.get("_hash")
                    if hash_value and result.get("status") == "succeeded":
                        results[hash_value] = result
                except json.JSONDecodeError:
                    continue

        return results
