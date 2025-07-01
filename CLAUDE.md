# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TroupeBot-v3 is a Python FastAPI web application that serves Google's Gemma 2 9B language model through a chat interface. The application is hosted at https://troupexbot.materiallab.io using Cloudflare Tunnel.

## Key Commands

### Setup Environment
```bash
# Initial setup (creates venv and installs dependencies)
./setup_gemma.sh

# Activate virtual environment
source venv/bin/activate
```

### Development
```bash
# Run the server locally
python server_fixed.py

# Check server logs during development
tail -f server_production.log
tail -f tunnel_production.log
```

### Production Deployment
```bash
# Start both server and Cloudflare tunnel
./run_production.sh

# This will:
# 1. Kill existing instances
# 2. Start server on port 8000
# 3. Start Cloudflare tunnel for public access
```

## Architecture

### Backend (`server_fixed.py`)
- FastAPI server using Uvicorn
- Loads Gemma 2 9B model with 4-bit quantization (BitsAndBytes) to reduce memory usage
- Endpoints:
  - `GET /` - Serves the web chat interface from static/index.html
  - `POST /generate` - Text generation endpoint accepting JSON with prompt, max_length, and temperature

### Frontend (`static/index.html`)
- Single-page vanilla JavaScript chat interface
- No build process or framework dependencies
- Communicates with backend via fetch API

### Model Configuration
- Model: `google/gemma-2-9b-it` from Hugging Face
- Uses 4-bit quantization with BitsAndBytesConfig
- Requires CUDA-capable GPU (~18GB model size)
- Chat template formatting is handled automatically by the tokenizer

## Development Notes

- No formal testing framework - test changes manually through the web interface
- No linting configuration - follow existing code style in server_fixed.py
- Dependencies are installed via setup_gemma.sh (no requirements.txt file)
- The server automatically downloads the model on first run if not cached
- Production logs are written to server_production.log and tunnel_production.log