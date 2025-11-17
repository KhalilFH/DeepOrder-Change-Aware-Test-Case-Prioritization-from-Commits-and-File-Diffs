#!/bin/bash
# Script to run DeepOrder with proper conda environment

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate deeporder-harsh

# Run the script (use first argument or default to DeepOrder)
SCRIPT="${1:-DeepOrder_on_google_Dataset.py}"
python "$SCRIPT"

# Deactivate when done
conda deactivate
