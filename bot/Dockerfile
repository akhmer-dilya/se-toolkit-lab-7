FROM python:3.14-slim

WORKDIR /bot

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy pyproject.toml for dependency installation
COPY pyproject.toml ./

# Install dependencies using uv (without lock file since we're in a workspace)
RUN uv sync --no-dev

# Copy bot source code
COPY bot.py ./
COPY handlers/ ./handlers/
COPY services/ ./services/
COPY config.py ./

# Run the bot
CMD ["uv", "run", "python", "bot.py"]
