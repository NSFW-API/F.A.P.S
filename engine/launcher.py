import asyncio
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp
import replicate

from helpers.retry import async_retry


class JobLauncher:
    def __init__(
            self,
            base_model: str,
            max_concurrency: int = 99,
            api_token: Optional[str] = None
    ):
        """
        Initialize the job launcher.
        
        Args:
            base_model: Replicate model identifier (e.g., "stability-ai/sdxl")
            max_concurrency: Maximum number of concurrent jobs
            api_token: Replicate API token (defaults to REPLICATE_API_TOKEN env var)
        """
        self.base_model = base_model
        self.max_concurrency = max_concurrency
        self.api_token = api_token or os.environ.get("REPLICATE_API_TOKEN")

        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN environment variable is not set")

        # Create a semaphore to limit concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)

        # Create a client session
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

    @async_retry(
        retries=5,
        base_delay=2.0,
        retry_on=[
            (aiohttp.ClientError, None),
            (Exception, "429"),
            (Exception, "5"),
        ]
    )
    async def launch_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Launch a job on Replicate.

        Args:
            params: Job parameters

        Returns:
            Job result including metadata
        """
        # Create a clean copy of params without special keys
        run_params = {}
        for k, v in params.items():
            if k.startswith('_'):
                continue  # Skip special keys

            # Extract primitive values
            if hasattr(v, 'static') and v.static is not None:
                run_params[k] = v.static
            elif hasattr(v, 'list') and v.list is not None and len(v.list) > 0:
                run_params[k] = v.list[0]  # Use first value
            elif hasattr(v, 'range') and v.range is not None:
                run_params[k] = v.range.start  # Use start value
            elif hasattr(v, 'random_int') and v.random_int is not None:
                run_params[k] = random.randint(v.random_int.min, v.random_int.max)
            else:
                # Use value as is if not a ParamValue
                run_params[k] = v

        for k in run_params.keys():
            # Convert specific parameters to strings for Chroma model
            if k in ["sampler_name", "scheduler"]:
                run_params[k] = str(run_params[k])
            # Make sure numeric parameters stay as numbers
            elif k in ["width", "height", "steps", "seed"]:
                if not isinstance(run_params[k], int):
                    run_params[k] = int(run_params[k])
            elif k in ["cfg"]:
                if not isinstance(run_params[k], float):
                    run_params[k] = float(run_params[k])

        # Record start time
        start_time = time.time()

        # Acquire semaphore to limit concurrency
        async with self.semaphore:
            # Set up the client with API token
            client = replicate.Client(api_token=self.api_token)

            try:
                # Print parameters for debugging
                print(f"Starting job with hash {params.get('_hash', 'unknown')}")
                print(f"Parameters: {run_params}")  # Print out params for debugging

                # Run the model
                output = await asyncio.to_thread(
                    client.run,
                    self.base_model,
                    input=run_params
                )

                # Calculate duration
                duration = time.time() - start_time

                # Default result is typically the image URL
                result_url = output[0] if isinstance(output, list) and output else output

                print(f"Job completed. Result URL: {result_url}")

                return {
                    "status": "succeeded",
                    "result_url": result_url,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat(),
                    "params": run_params,
                    "_hash": params.get("_hash")
                }
            except Exception as e:
                # Print detailed error for debugging
                import traceback
                print(f"Error launching job: {e}")
                print(traceback.format_exc())
                raise

    async def launch_jobs(self, param_combinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Launch multiple jobs in parallel.
        
        Args:
            param_combinations: List of parameter combinations
            
        Returns:
            List of job results
        """
        tasks = [self.launch_job(params) for params in param_combinations]
        return await asyncio.gather(*tasks, return_exceptions=True)
