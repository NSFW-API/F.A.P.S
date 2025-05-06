from setuptools import setup, find_packages

setup(
    name="faps",
    version="0.1.0",
    description="F.A.P.S. (Fine-tuned Analytical Parameter Sweeper) - A lightweight CLI tool that launches many image-generation jobs on Replicate in parallel",
    author="The NSFW Company Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "replicate>=0.13.0",
        "aiohttp>=3.8.5",
        "pydantic>=2.0.0",
        "PyYAML>=6.0",
        "jinja2>=3.1.2",
        "Pillow>=9.5.0",
        "tqdm>=4.65.0",
        "numpy>=1.24.0",
        "python-dotenv>=0.19.0"  # Added python-dotenv
    ],
    entry_points={
        'console_scripts': [
            'faps=cli:main',
        ],
    },
)