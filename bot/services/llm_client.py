"""LLM client for tool calling.

This client talks to the Qwen Code API (OpenAI-compatible) and supports
tool/function calling. The LLM decides which tools to call based on
the user's message and tool descriptions.
"""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class LLMClient:
    """Client for the LLM API with tool calling support."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a request to the LLM API."""
        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise LLMClientError(f"LLM timeout: {str(e)}", e)
        except httpx.ConnectError as e:
            raise LLMClientError(f"LLM connection failed: {str(e)}", e)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMClientError(
                    "LLM error: HTTP 401 Unauthorized. Token may be expired. "
                    "Try: cd ~/qwen-code-oai-proxy && docker compose restart",
                    e,
                )
            raise LLMClientError(f"LLM error: HTTP {e.response.status_code}", e)
        except Exception as e:
            raise LLMClientError(f"LLM error: {str(e)}", e)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat message to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions (OpenAI function schema)
            system_prompt: Optional system prompt

        Returns:
            LLM response dict with 'content' and/or 'tool_calls'
        """
        # Build messages list
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = self._request(payload)

        # Extract choice
        choices = response.get("choices", [])
        if not choices:
            raise LLMClientError("LLM returned no choices")

        choice = choices[0]
        message = choice.get("message", {})

        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", []),
        }
