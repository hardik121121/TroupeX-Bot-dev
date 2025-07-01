# Gemma 2 9B Chat Interface

A web-based chat interface for Google's Gemma 2 9B model, hosted at https://troupexbot.materiallab.io

## Core Files

- `server_fixed.py` - Main FastAPI server with web UI
- `run_production.sh` - Production startup script
- `static/index.html` - Chat web interface

## Running the Service

```bash
./run_production.sh
```

This starts:
1. The Gemma 2 9B model server on port 8000
2. Cloudflare tunnel for public access

## Logs

- Server: `server_production.log`
- Tunnel: `tunnel_production.log`

## Requirements

- Python 3.8+
- CUDA-capable GPU (currently using RTX 4500)
- ~18GB free disk space for model
- Virtual environment with dependencies installed

## API Endpoints

- `GET /` - Web chat interface
- `POST /generate` - Generate text completions

Request format:
```json
{
  "prompt": "Your question here",
  "max_length": 512,
  "temperature": 0.7
}
```