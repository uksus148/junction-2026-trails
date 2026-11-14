"""One validated tool result over Anthropic or Groq, without automatic retries."""

import asyncio
import json
import re
import time

import httpx

from gopstop_agent.config import Settings


class ProviderError(Exception):
    """An upstream response could not be used; never expose its body to clients."""


class ProviderTimeout(ProviderError):
    """A provider or internal discovery deadline elapsed."""


class ToolModel:
    def __init__(self, client: httpx.AsyncClient, key: str, provider: str = "anthropic",
                 timeout_seconds: float = 20) -> None:
        if provider not in ("anthropic", "groq"):
            raise ValueError("Unknown LLM provider.")
        self.provider, self._client, self._key = provider, client, key
        self._timeout = httpx.Timeout(timeout_seconds)
        self._lock = asyncio.Lock()
        self._remaining, self._reset = None, 0.0

    async def call(self, body: dict) -> dict:
        name = body["tool_choice"]["name"]
        try:
            if self.provider == "groq":
                payload = {
                    "model": body["model"], "max_completion_tokens": max(2048, body["max_tokens"]),
                    "messages": [{"role": "system", "content": body["system"]}, *body["messages"]],
                    "tools": [{"type": "function", "function": {
                        "name": tool["name"], "description": tool["description"],
                        "parameters": tool["input_schema"],
                    }} for tool in body["tools"]],
                    "tool_choice": {"type": "function", "function": {"name": name}},
                    "parallel_tool_calls": False,
                }
                if body["model"].startswith("openai/gpt-oss-"):
                    payload["reasoning_effort"] = "low"
                # Shared by intent/resolution/reply in one worker. Outer chat/discovery
                # deadlines include waiting; 429 responses are never replayed.
                async with self._lock:
                    encoded = json.dumps(payload, ensure_ascii=False)
                    estimate = max(len(encoded) // 2, len(encoded.encode()) // 3) + payload["max_completion_tokens"]
                    if self._remaining is not None and self._remaining < estimate:
                        await asyncio.sleep(max(0, self._reset - time.monotonic()))
                    response = await self._client.post(
                        "https://api.groq.com/openai/v1/chat/completions", json=payload,
                        headers={"Authorization": f"Bearer {self._key}"},
                        timeout=self._timeout, follow_redirects=False,
                    )
                    remaining = response.headers.get("x-ratelimit-remaining-tokens", "")
                    self._remaining = int(remaining) if remaining.isdigit() else None
                    reset = response.headers.get("x-ratelimit-reset-tokens", "")
                    seconds = sum(float(n) * {"ms": .001, "s": 1, "m": 60, "h": 3600}[unit]
                                  for n, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", reset))
                    self._reset = time.monotonic() + seconds
                response.raise_for_status()
                choices = response.json()["choices"]
                if len(choices) != 1 or choices[0]["finish_reason"] not in ("tool_calls", "stop"):
                    raise ProviderError("Model tool generation did not complete.")
                calls = choices[0]["message"]["tool_calls"]
                if len(calls) != 1 or calls[0]["type"] != "function" or calls[0]["function"]["name"] != name:
                    raise ProviderError("Model returned an unexpected tool.")
                result = json.loads(calls[0]["function"]["arguments"])
            else:
                response = await self._client.post(
                    "https://api.anthropic.com/v1/messages", json=body,
                    headers={"x-api-key": self._key, "anthropic-version": "2023-06-01"},
                    timeout=self._timeout, follow_redirects=False,
                )
                response.raise_for_status()
                data = response.json()
                calls = [item for item in data["content"] if item.get("type") == "tool_use"]
                if data.get("stop_reason") != "tool_use" or len(calls) != 1 or calls[0]["name"] != name:
                    raise ProviderError("Model returned an incomplete or unexpected tool.")
                result = calls[0]["input"]
            if not isinstance(result, dict):
                raise ProviderError("Model tool input must be an object.")
            return result
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("Model request is temporarily unavailable (timeout).") from exc
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("Model request is temporarily unavailable.") from exc


def create_tool_model(client: httpx.AsyncClient, settings: Settings) -> ToolModel:
    return ToolModel(client, settings.llm_key.get_secret_value(), settings.llm_provider,
                     settings.provider_timeout_seconds)
