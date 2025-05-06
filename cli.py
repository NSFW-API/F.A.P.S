import argparse
import os
import asyncio
from pathlib import Path
import json
from typing import Dict, Any, List, Optional, Tuple
import sys
from tqdm import tqdm

# Add dotenv to load environment variables from .env file
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use absolute imports
from config.loader import load_config
from config.builder import build_combinations, get_param_metadata
from engine.launcher import JobLauncher
from engine.collector import ResultCollector
from renderers.grid import GridRenderer


async def run_sweep(args):
    """Run a parameter sweep with the given arguments."""
    # Load the configuration
    config = load_config(args.config)
    
    # Create output directory path
    output_dir = Path(config.meta.get("output_dir", "./runs")) / config.meta.get("name", "sweep")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save a copy of the config
    config_path = output_dir / "cfg.yaml"
    try:
        # Try using model_dump() for Pydantic v2
        config_dict = config.model_dump()
    except AttributeError:
        # Fall back to dict() for older versions
        config_dict = config.dict()

    with open(config_path, "w") as f:
        f.write(json.dumps(config_dict, indent=2))
    
    print(f"Loaded configuration '{config.meta.get('name')}', output directory: {output_dir}")
        
    # Build parameter combinations
    combinations = build_combinations(config)
    
    print(f"Generated {len(combinations)} parameter combinations")
    
    # Initialize the result collector
    collector = ResultCollector(output_dir, overwrite=args.overwrite)
    
    # Load previous results for resumability
    prev_results = {}
    if not args.overwrite:
        prev_results = collector.load_previous_results()
        print(f"Found {len(prev_results)} previous results")
    
    # Filter combinations to only those that need to be run
    pending_combinations = []
    for combo in combinations:
        hash_value = combo.get("_hash")
        if hash_value and hash_value in prev_results:
            if not args.retry_failed or prev_results[hash_value].get("status") == "succeeded":
                continue
        pending_combinations.append(combo)
    
    if not pending_combinations:
        print("All combinations have already been processed. Use --overwrite to force reprocessing.")
        
        # Render the grid even if no new combinations
        all_results = list(prev_results.values())
        print(f"Rendering grid with {len(all_results)} results...")
        grid_renderer = GridRenderer(output_dir, config)
        grid_path = grid_renderer.render_grid(all_results)
        print(f"Grid rendered to {grid_path}")
        return
    
    print(f"Running {len(pending_combinations)} pending combinations")
    
    # Initialize the job launcher
    async with JobLauncher(
        base_model=config.meta.get("base_model"),
        max_concurrency=args.concurrency
    ) as launcher, collector as collector:
        
        # Launch jobs with progress bar
        with tqdm(total=len(pending_combinations), desc="Launching jobs") as progress:
            tasks = []
            for combo in pending_combinations:
                task = asyncio.create_task(launcher.launch_job(combo))
                task.add_done_callback(lambda _: progress.update(1))
                tasks.append(task)
            
            results = []
            for task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append({"status": "failed", "error": str(e)})
        
        # Collect results with progress bar
        with tqdm(total=len(results), desc="Collecting results") as progress:
            collection_tasks = []
            for result in results:
                task = asyncio.create_task(collector.collect_result(result))
                task.add_done_callback(lambda _: progress.update(1))
                collection_tasks.append(task)
            
            collected_results = []
            for task in collection_tasks:
                try:
                    collected = await task
                    collected_results.append(collected)
                except Exception as e:
                    collected_results.append({"status": "failed", "error": str(e)})
    
    # Combine with previous results
    all_results = list(prev_results.values()) + collected_results
    
    # Render the grid
    print(f"Rendering grid with {len(all_results)} results...")
    grid_renderer = GridRenderer(output_dir, config)
    grid_path = grid_renderer.render_grid(all_results)
    
    print(f"Grid rendered to {grid_path}")
    print(f"Sweep complete. {len(collected_results)} new results processed.")


def create_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="F.A.P.S. (Fine-tuned Analytical Parameter Sweeper) - A tool for sweeping over image generation parameters",
    )
    
    # Main subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a parameter sweep")
    run_parser.add_argument("config", help="Path to the configuration file (YAML or JSON)")
    run_parser.add_argument("--concurrency", "-c", type=int, default=8,
                          help="Maximum number of concurrent jobs (default: 8)")
    run_parser.add_argument("--overwrite", "-o", action="store_true",
                          help="Overwrite existing results")
    run_parser.add_argument("--retry-failed", "-r", action="store_true",
                          help="Retry failed jobs")
    
    # Render command (to regenerate grid from existing results)
    render_parser = subparsers.add_parser("render", help="Render a grid from existing results")
    render_parser.add_argument("config", help="Path to the configuration file (YAML or JSON)")
    
    # Template command (to generate a template configuration)
    template_parser = subparsers.add_parser("template", help="Generate a template configuration")
    template_parser.add_argument("output", help="Output file path")
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Check for API token
    if not os.environ.get("REPLICATE_API_TOKEN") and args.command == "run":
        print("Error: REPLICATE_API_TOKEN environment variable is not set.")
        print("You can set it with: export REPLICATE_API_TOKEN=your_token_here")
        print("Or add it to your .env file.")
        return 1
    
    if args.command == "run":
        asyncio.run(run_sweep(args))
    elif args.command == "render":
        render_grid(args)
    elif args.command == "template":
        generate_template(args)
    
    return 0


def render_grid(args):
    """Render a grid from existing results."""
    # Load the configuration
    config = load_config(args.config)
    
    # Get output directory
    output_dir = Path(config.meta.get("output_dir", "./runs")) / config.meta.get("name", "sweep")
    
    if not output_dir.exists():
        print(f"Error: Output directory {output_dir} does not exist.")
        return 1
    
    # Load results
    collector = ResultCollector(output_dir)
    results = list(collector.load_previous_results().values())
    
    if not results:
        print("Error: No results found in the output directory.")
        return 1
    
    # Render the grid
    print(f"Rendering grid with {len(results)} results...")
    grid_renderer = GridRenderer(output_dir, config)
    grid_path = grid_renderer.render_grid(results)
    
    print(f"Grid rendered to {grid_path}")
    return 0


def generate_template(args):
    """Generate a template configuration file."""
    output_path = Path(args.output)
    
    # Create template configuration
    template = {
        "meta": {
            "name": "my_sweep",
            "base_model": "stability-ai/sdxl:latest",
            "output_dir": "./runs"
        },
        "grid_axes": {
            "rows": "cfg",
            "cols": "steps"
        },
        "params": {
            "prompt": {
                "static": "A beautiful landscape with mountains and a lake"
            },
            "width": {
                "static": 1024
            },
            "height": {
                "static": 1024
            },
            "sampler": {
                "static": "euler_a"
            },
            "scheduler": {
                "static": "karras"
            },
            "seed": {
                "random_int": {
                    "min": 1,
                    "max": 4294967295
                }
            },
            "cfg": {
                "range": {
                    "start": 4,
                    "end": 16,
                    "step": 4
                }
            },
            "steps": {
                "list": [20, 40, 60]
            }
        }
    }
    
    # Write to file
    extension = output_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if extension == '.yaml' or extension == '.yml':
        import yaml
        with open(output_path, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
    else:
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2)
    
    print(f"Template configuration generated at {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
