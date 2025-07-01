#!/bin/bash
set -e

echo "Setting up Gemma 2 7B LLM Server..."

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers accelerate bitsandbytes
pip install fastapi uvicorn pydantic
pip install cloudflared

# Create directory for model
mkdir -p models

echo "Setup complete! Virtual environment created."
echo "To download the model and start the server, run: source venv/bin/activate && python server.py"