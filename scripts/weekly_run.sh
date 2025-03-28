#!/bin/bash

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate research-digest

# Change to the project directory
cd "$(dirname "$0")/.."

# Run the main script
python src/main.py --interval biweekly --max-papers 50

# Optional: Push blog post to website
# Add commands to push to your website here