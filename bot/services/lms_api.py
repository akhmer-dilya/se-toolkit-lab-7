"""LMS API client for the Telegram bot.

Handles HTTP requests to the LMS backend with Bearer token authentication.
All errors are caught and returned as user-friendly messages that include
the actual error details (not raw tracebacks, not vague messages).
"""

import httpx
from typing import Any


class LMSAPIError(Exception):
    """Base exception for LMS API errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class LMSAPIClient:
    """Client for the LMS backend API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10.0,
        )

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request with error handling."""
        try:
            response = self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise LMSAPIError(
                f"Backend timeout: connection timed out ({self.base_url}{endpoint}). "
                "The backend may be overloaded or unreachable.",
                e,
            )
        except httpx.ConnectError as e:
            error_msg = str(e).lower()
            if "connection refused" in error_msg:
                raise LMSAPIError(
                    f"Backend error: connection refused ({self.base_url}). "
                    "Check that the backend service is running.",
                    e,
                )
            elif "nodename nor servname provided" in error_msg:
                raise LMSAPIError(
                    f"Backend error: invalid host ({self.base_url}). "
                    "Check the LMS_API_BASE_URL configuration.",
                    e,
                )
            else:
                raise LMSAPIError(
                    f"Backend error: connection failed ({self.base_url}). {str(e)}",
                    e,
                )
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise LMSAPIError(
                    f"Backend error: HTTP 401 Unauthorized. The LMS_API_KEY may be invalid.",
                    e,
                )
            elif status_code == 403:
                raise LMSAPIError(
                    f"Backend error: HTTP 403 Forbidden. Access denied.",
                    e,
                )
            elif status_code == 404:
                raise LMSAPIError(
                    f"Backend error: HTTP 404 Not Found ({endpoint}).",
                    e,
                )
            elif status_code >= 500:
                raise LMSAPIError(
                    f"Backend error: HTTP {status_code} {e.response.reason_phrase}. "
                    "The backend service may be down.",
                    e,
                )
            else:
                raise LMSAPIError(
                    f"Backend error: HTTP {status_code} {e.response.reason_phrase}.",
                    e,
                )
        except Exception as e:
            raise LMSAPIError(
                f"Backend error: unexpected error ({str(e)}).",
                e,
            )

    def get_items(self) -> list[dict[str, Any]]:
        """Get all items (labs and tasks)."""
        response = self._request("GET", "/items/")
        return response.json()

    def get_learners(self) -> list[dict[str, Any]]:
        """Get all enrolled learners."""
        response = self._request("GET", "/learners/")
        return response.json()

    def get_analytics_scores(self, lab: str) -> dict[str, Any]:
        """Get score distribution for a lab."""
        response = self._request("GET", "/analytics/scores", params={"lab": lab})
        return response.json()

    def get_analytics_pass_rates(self, lab: str) -> dict[str, Any]:
        """Get per-task pass rates for a lab."""
        response = self._request("GET", "/analytics/pass-rates", params={"lab": lab})
        return response.json()

    def get_analytics_timeline(self, lab: str) -> dict[str, Any]:
        """Get submissions timeline for a lab."""
        response = self._request("GET", "/analytics/timeline", params={"lab": lab})
        return response.json()

    def get_analytics_groups(self, lab: str) -> dict[str, Any]:
        """Get per-group performance for a lab."""
        response = self._request("GET", "/analytics/groups", params={"lab": lab})
        return response.json()

    def get_analytics_top_learners(self, lab: str, limit: int = 5) -> dict[str, Any]:
        """Get top N learners for a lab."""
        response = self._request(
            "GET", "/analytics/top-learners", params={"lab": lab, "limit": limit}
        )
        return response.json()

    def get_analytics_completion_rate(self, lab: str) -> dict[str, Any]:
        """Get completion rate for a lab."""
        response = self._request(
            "GET", "/analytics/completion-rate", params={"lab": lab}
        )
        return response.json()

    def sync_pipeline(self) -> dict[str, int]:
        """Trigger ETL pipeline sync."""
        response = self._request("POST", "/pipeline/sync", json={})
        return response.json()

    def health_check(self) -> dict[str, Any]:
        """Check if backend is healthy by fetching items."""
        items = self.get_items()
        return {"healthy": True, "item_count": len(items)}
