"""Optional Hindsight memory for research adapters."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit


DEFAULT_URL = "http://localhost:8888"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_MEMORY_CHARS = 12_000
ENVIRONMENT = (
    "OMR_HINDSIGHT_BANK",
    "HINDSIGHT_API_URL",
    "HINDSIGHT_API_KEY",
)


class HindsightError(RuntimeError):
    """A Hindsight request or response was invalid."""


@dataclass(frozen=True)
class Hindsight:
    base_url: str
    bank_id: str
    api_key: str | None = None
    timeout: float = 5.0

    def __post_init__(self) -> None:
        base_url = self.base_url.rstrip("/")
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("HINDSIGHT_API_URL must be an HTTP or HTTPS URL")
        if not self.bank_id:
            raise ValueError("OMR_HINDSIGHT_BANK cannot be empty")
        object.__setattr__(self, "base_url", base_url)

    def recall(self, query: str) -> str:
        response = self.post(
            "memories/recall",
            {
                "query": query,
                "types": ["world", "experience", "observation"],
                "prefer_observations": True,
                "budget": "low",
                "max_tokens": 1024,
            },
        )
        results = response.get("results")
        if not isinstance(results, list):
            raise HindsightError("recall response has no results list")

        memories = []
        for result in results:
            if not isinstance(result, dict) or not isinstance(result.get("text"), str):
                raise HindsightError("recall response contains an invalid result")
            text = result["text"].strip()
            if text:
                memories.append(f"- {text}")
        return "\n".join(memories)[:MAX_MEMORY_CHARS]

    def retain(
        self,
        content: str,
        document_id: str,
        metadata: dict[str, str],
        context: str,
    ) -> None:
        response = self.post(
            "memories",
            {
                "items": [
                    {
                        "content": content,
                        "context": context,
                        "document_id": document_id,
                        "metadata": metadata,
                    }
                ],
                "async": True,
            },
        )
        if response.get("success") is not True:
            raise HindsightError("retain response was not successful")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        bank = quote(self.bank_id, safe="")
        url = f"{self.base_url}/v1/default/banks/{bank}/{path}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "one-more-run/0.1",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, allow_nan=False, separators=(",", ":")).encode(),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            raise HindsightError(f"server returned HTTP {error.code}") from error
        except (OSError, TimeoutError) as error:
            raise HindsightError(f"request failed: {error}") from error
        if len(body) > MAX_RESPONSE_BYTES:
            raise HindsightError("response is too large")
        try:
            value = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise HindsightError("server returned invalid JSON") from error
        if not isinstance(value, dict):
            raise HindsightError("server returned a non-object response")
        return value


def from_environment(environment: Mapping[str, str]) -> Hindsight | None:
    bank_id = environment.get("OMR_HINDSIGHT_BANK")
    if not bank_id:
        return None
    return Hindsight(
        base_url=environment.get("HINDSIGHT_API_URL", DEFAULT_URL),
        bank_id=bank_id,
        api_key=environment.get("HINDSIGHT_API_KEY"),
    )
