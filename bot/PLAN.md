# LMS Telegram Bot - Development Plan

## Overview

This document outlines the implementation plan for the LMS Telegram bot across four tasks. The bot provides a conversational interface to the Learning Management System, allowing students to check their scores, view available labs, and ask questions using natural language.

## Architecture

The bot follows a **layered architecture** with clear separation of concerns:

1. **Entry Point (`bot.py`)**: Handles Telegram client initialization and `--test` mode
2. **Handlers (`handlers/`)**: Pure functions that process commands and return responses
3. **Services (`services/`)**: External API clients (LMS backend, LLM)
4. **Configuration (`config.py`)**: Environment variable loading with pydantic-settings

This architecture enables **testable handlers** — the same handler functions work in `--test` mode, unit tests, and production Telegram mode without modification.

## Task 1: Scaffold and Test Mode

**Goal**: Create the bot skeleton with `--test` mode support.

- Create `bot/` directory structure
- Implement placeholder handlers for `/start`, `/help`, `/health`, `/labs`, `/scores`
- Add `--test` flag support: `uv run bot.py --test "/start"` prints response to stdout
- Create `pyproject.toml` with dependencies (aiogram, httpx, pydantic-settings)
- Write this development plan

**Acceptance**: All commands return non-empty output and exit with code 0.

## Task 2: Backend Integration

**Goal**: Connect handlers to the LMS backend API.

- Create `services/lms_api.py` — HTTP client with Bearer token authentication
- Implement real `/health` handler that checks backend connectivity
- Implement `/labs` handler that fetches labs from `GET /items/`
- Implement `/scores` handler that fetches student scores
- Handle API errors gracefully (timeouts, authentication failures, empty responses)

**Key pattern**: API client reads `LMS_API_BASE_URL` and `LMS_API_KEY` from environment. This enables testing against different deployments without code changes.

## Task 3: Intent Routing with LLM

**Goal**: Enable natural language queries using LLM tool calling.

- Create `services/llm_client.py` — LLM client with tool calling support
- Define tools for each handler (get_labs, get_scores, get_health)
- Implement intent router that lets LLM decide which tool to call
- Handle plain text queries like "what labs are available?" or "show my scores for lab 04"

**Key insight**: The LLM reads tool descriptions to decide which to call. Description quality matters more than prompt engineering. If the LLM picks the wrong tool, improve the tool description — don't route around it with regex.

## Task 4: Deployment

**Goal**: Deploy the bot on the VM and run it as a service.

- Create systemd service file for the bot
- Configure Docker networking (containers use service names, not `localhost`)
- Set up health checks and automatic restart
- Verify bot responds in Telegram and via `--test` mode on the VM

**Key concept**: Docker containers communicate via service names from `docker-compose.yml`. The bot container uses `http://backend:8000` not `http://localhost:42001`.

## Testing Strategy

1. **Test mode**: `uv run bot.py --test "/command"` for quick iteration
2. **Unit tests**: Test handlers directly with mocked services
3. **Integration tests**: Test full flow with real API calls (staging environment)
4. **Manual testing**: Send commands to bot in Telegram

## File Structure

```
bot/
├── bot.py              # Entry point with --test mode
├── config.py           # Environment loading
├── pyproject.toml      # Dependencies
├── PLAN.md             # This file
├── handlers/
│   ├── __init__.py     # Command handlers
│   └── intent.py       # LLM intent router (Task 3)
└── services/
    ├── __init__.py
    ├── lms_api.py      # LMS API client (Task 2)
    └── llm_client.py   # LLM client (Task 3)
```

## Risks and Mitigations

- **API failures**: All service calls wrapped in try/except with user-friendly error messages
- **LLM rate limits**: Cache responses where appropriate, implement retry logic
- **Token exposure**: Never commit `.env.bot.secret`; use gitignore
- **Docker networking**: Test locally first, then deploy to VM with same configuration
