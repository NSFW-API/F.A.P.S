# F.A.P.S. (Fine-tuned Analytical Parameter Sweeper)

A lightweight CLI tool that launches many image-generation jobs on Replicate in parallel, sweeping over user-defined
parameter combinations, then collates the outputs into a browsable HTML grid.

## Features

- **Rapid experimentation** - Explore model behavior across prompts and numeric parameters without manual repetition
- **Reproducibility** - Every sweep is driven by a single YAML config and can be resumed or shared
- **Visual insight** - Auto-generated grid offers side-by-side comparison, with light-box and multi-select compare for
  deeper inspection
- **Extensibility** - Architecture leaves hooks for future back-ends (local ComfyUI, Modal), metrics, and video support

## Installation

### Prerequisites

- Python 3.10 or later
- A Replicate API token (get one at [replicate.com](https://replicate.com))

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/NSFW-API/F.A.P.S.git
   cd F.A.P.S
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the package in development mode**
   ```bash
   pip install -e .
   ```

4. **Set up your API token**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit the .env file and replace with your actual token
   # REPLICATE_API_TOKEN=r8_your_token_here
   ```

## Quick Start

### 1. Create a configuration file

You can copy and modify the example configuration:

```bash
cp example-config.yaml sweep_configs/my_sweep.yaml
```

Or generate a template:

```bash
python cli.py template sweep_configs/my_sweep.yaml
```

### 2. Edit the configuration file

Customize the YAML file according to your needs:

```yaml
meta:
  name: "prompt_vs_cfg"
  base_model: "stability-ai/sdxl:latest"
  output_dir: "./runs"

grid_axes:
  rows: "prompt"
  cols: "cfg"

params:
  # Varying parameters
  prompt:
    list:
      - "A serene mountain landscape with a clear lake at sunset"
      - "A futuristic cityscape with flying cars and neon lights"
      - "A cozy cottage in a forest clearing with warm light from the windows"

  cfg:
    range:
      start: 4.0
      end: 12.0
      step: 2.0

  # Static parameters
  width:
    static: 1024

  height:
    static: 1024

  sampler:
    static: "euler_a"

  scheduler:
    static: "karras"

  steps:
    static: 40

  # Random seed (generates a new random value for each combination)
  seed:
    random_int:
      min: 1
      max: 4294967295
```

### 3. Run your experiment

```bash
# Make sure your virtual environment is active and API token is set
python cli.py run sweep_configs/my_sweep.yaml

# Or if the CLI was properly installed:
faps run sweep_configs/my_sweep.yaml
```

Additional options:

```bash
# Set concurrency level
python cli.py run sweep_configs/my_sweep.yaml --concurrency 4

# Overwrite existing results
python cli.py run sweep_configs/my_sweep.yaml --overwrite

# Retry failed jobs
python cli.py run sweep_configs/my_sweep.yaml --retry-failed
```

### 4. View the results

After completion, open the generated HTML grid in your browser:

```bash
# For Linux/macOS
open runs/prompt_vs_cfg/grid.html

# For Windows
start runs/prompt_vs_cfg/grid.html
```

### Troubleshooting

- If the `faps` command isn't available, use `python cli.py` instead
- If you see "REPLICATE_API_TOKEN environment variable is not set", check your `.env` file and make sure it's in the
  correct location

## Configuration Files

Place your sweep configuration YAML files in the `sweep_configs/` directory. These files are git-ignored by default to avoid committing potentially sensitive parameters or API information.

Example configuration files can be found in the project root:
- `example-config.yaml` - Basic parameter sweep template

## Grid Interaction

- **Thumbnail grid** - Lightweight JPG thumbs
- **Light-box** - Click to view full PNG + param JSON
- **Compare mode** - Ctrl/⌘-click multi-select → floating button → overlay with all selected full-res images

## Directory Layout

```
├ sweep_configs/      # User configuration YAML files (git-ignored)
└ runs/<sweep_name>/  # Generated output
  ├ cfg.yaml          # Copy of configuration used
  ├ sweep_log.jsonl   # Job results log
  ├ grid.html         # Generated visual grid
  └ outputs/          # Result artifacts
    └ <hash>/         # One directory per parameter combination
      ├ params.json   # Parameters used
      ├ output.png    # Original output image
      └ thumb.jpg     # Thumbnail for grid
```

## Parameter Types

- `static`: A single fixed value
- `list`: A list of discrete values to sweep over
- `range`: A range of values with a step size
- `random_int`: A random integer within a range (generates one value per run)

## Rendering Without Running

If you just want to regenerate the HTML grid without running any new jobs:

```bash
python cli.py render sweep_configs/my_sweep.yaml
```

## Future Plans (Post-MVP)

- Video support with MP4 artifacts and FFmpeg thumb extraction
- LoRA & ControlNet parameter sweeping
- Automatic metric scoring (CLIP similarity, face detection)
- Streamlit GUI for easier configuration
- Multi-checkpoint sweeps and cloud storage upload

## License

MIT