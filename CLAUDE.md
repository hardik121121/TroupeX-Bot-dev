# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TroupeBot-v3 is an AI-powered assistant for entertainment professionals using Google's Gemma 2 9B model. It provides role-specific onboarding and creative assistance through a 4-stage conversation flow, hosted at https://troupexbot.materiallab.io via Cloudflare Tunnel.

## Key Commands

### Setup & Development
```bash
# Initial setup (creates venv and installs dependencies)
./setup_gemma.sh

# Activate virtual environment
source venv/bin/activate

# Run server locally (port 8000)
python server_fixed.py

# Monitor logs during development
tail -f server_production.log
tail -f tunnel_production.log
```

### Production Deployment
```bash
# Deploy to production (starts server + Cloudflare tunnel)
./run_production.sh
```

## Architecture

### Core Components

**`server_fixed.py`** - Main application server
- FastAPI with session management (UUID-based, in-memory)
- 4-stage conversation flow: Introduction → Profile Building → Redirect → Assistant Mode
- Endpoints: `/` (landing), `/chat` (interface), `/generate` (API)
- Model: Gemma 2 9B with 4-bit quantization via BitsAndBytes

**`system_prompt.md`** - Bot personality and behavior
- Defines TroupeBot's character and conversation stages
- Controls role detection and question flow

**`role_questions.json`** - Role-specific questions
- 20+ entertainment professions supported
- 3-5 questions per role for profile building

### Frontend Structure
- `static/index.html` - Landing page with animated background
- `static/chat.html` - Chat interface with glassmorphism design
- Pure vanilla JavaScript, no build process required

## Development Guidelines

### Testing Changes
Manual testing approach - use `deployment_checklist.md` as reference:
- Test all conversation stages
- Verify role detection (including typos)
- Check session persistence
- Monitor performance under load

### Common Modifications

**Update bot personality**: Edit `system_prompt.md`, restart server

**Add new role**: Update `role_questions.json` with new profession and questions

**Frontend changes**: Edit HTML/CSS/JS directly in `static/` directory

**Server behavior**: Modify `server_fixed.py`, focusing on:
- `generate_response()` for conversation logic
- `detect_role()` for role matching
- Session management in global `sessions` dict

### Important Patterns

1. **Role Detection**: Uses comprehensive pattern matching with typo tolerance in `detect_role()`
2. **Session State**: Tracks conversation stage, role, and questions asked per session
3. **Question Management**: Prevents duplicate questions within a session
4. **Error Handling**: All exceptions logged, graceful fallbacks provided

## Performance & Limitations

- Model requires ~18GB GPU memory (reduced via 4-bit quantization)
- Sessions are in-memory only (lost on restart)
- No database - all state is ephemeral
- Production handles 10+ concurrent users comfortably

## Deployment Notes

- Server runs on port 8000 by default
- Cloudflare tunnel configuration is managed by `run_production.sh`
- Logs are written to `server_production.log` and `tunnel_production.log`
- Model downloads automatically on first run if not cached