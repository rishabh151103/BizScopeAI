import os
import time
import logging
import json
from time import perf_counter

import requests
from pydantic import BaseModel


logger = logging.getLogger(__name__)


OLLAMA_URL = os.getenv(
    "BIZSCOPE_OLLAMA_URL",
    "http://localhost:11434/api/chat",
)

GENERAL_MODEL = os.getenv("BIZSCOPE_GENERAL_MODEL", "gemma3:4b")
PLANNER_MODEL = os.getenv("BIZSCOPE_PLANNER_MODEL", "qwen3:4b")

try:
    OLLAMA_TIMEOUT_SECONDS = max(
        1,
        int(os.getenv("BIZSCOPE_OLLAMA_TIMEOUT_SECONDS", "300")),
    )
    OLLAMA_CONNECT_TIMEOUT_SECONDS = max(
        1,
        int(os.getenv("BIZSCOPE_OLLAMA_CONNECT_TIMEOUT_SECONDS", "5")),
    )
    MAX_RETRIES = max(0, int(os.getenv("BIZSCOPE_LLM_MAX_RETRIES", "1")))
    TEXT_MAX_OUTPUT_TOKENS = max(
        64,
        int(os.getenv("BIZSCOPE_LLM_MAX_OUTPUT_TOKENS", "768")),
    )
    TEXT_CONTEXT_TOKENS = max(
        2048,
        int(os.getenv("BIZSCOPE_LLM_NUM_CTX", "8192")),
    )
except ValueError as exc:
    raise RuntimeError(
        "Ollama timeout, retry, context, and output-token settings must be integers."
    ) from exc

RETRY_BACKOFF_SECONDS = 1

RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class OllamaCallError(RuntimeError):
    """A safe, user-facing category for failures from the local model server."""


class OllamaTimeoutError(OllamaCallError):
    def __init__(self, model: str, timeout_seconds: int, attempts: int):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.attempts = attempts
        super().__init__(
            f"Ollama model {model} did not respond within "
            f"{timeout_seconds} seconds."
        )


class OllamaUnavailableError(OllamaCallError):
    def __init__(self, model: str, attempts: int):
        self.model = model
        self.attempts = attempts
        super().__init__("The local Ollama service could not be reached.")


def call_ollama(
    data,
    model,
    max_retries=0,
):
    payload = data.copy()
    payload["model"] = model

    last_error = None

    for attempt in range(max_retries + 1):
        attempt_started = perf_counter()
        try:

            logger.debug(
                "Ollama request model=%s format_present=%s",
                payload.get("model"),
                bool(payload.get("format")),
            )
            
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=(
                    OLLAMA_CONNECT_TIMEOUT_SECONDS,
                    OLLAMA_TIMEOUT_SECONDS,
                ),
            )

            if response.status_code in RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(
                    f"Ollama returned HTTP {response.status_code}",
                    response=response,
                )

            response.raise_for_status()

            result = response.json()
            logger.info(
                "ollama_call model=%s attempt=%s outcome=success "
                "duration_ms=%.1f format_present=%s",
                model,
                attempt + 1,
                (perf_counter() - attempt_started) * 1000,
                bool(payload.get("format")),
            )
            return result

        except requests.HTTPError as exc:
            last_error = exc

            response = exc.response
            status_code = response.status_code if response is not None else None
            logger.warning(
                "ollama_call model=%s attempt=%s outcome=http_error "
                "status_code=%s duration_ms=%.1f",
                model,
                attempt + 1,
                status_code,
                (perf_counter() - attempt_started) * 1000,
            )

            if (
                response is not None
                and response.status_code not in RETRYABLE_STATUS_CODES
            ):
                raise OllamaCallError(
                    f"Ollama returned HTTP {response.status_code}."
                ) from exc

        except requests.ConnectTimeout as exc:
            last_error = exc
            logger.warning(
                "ollama_call model=%s attempt=%s outcome=connect_timeout "
                "duration_ms=%.1f",
                model,
                attempt + 1,
                (perf_counter() - attempt_started) * 1000,
            )

        except requests.Timeout as exc:
            last_error = exc
            logger.warning(
                "ollama_call model=%s attempt=%s outcome=read_timeout "
                "duration_ms=%.1f",
                model,
                attempt + 1,
                (perf_counter() - attempt_started) * 1000,
            )

        except requests.ConnectionError as exc:
            last_error = exc
            logger.warning(
                "ollama_call model=%s attempt=%s outcome=connection_error "
                "duration_ms=%.1f",
                model,
                attempt + 1,
                (perf_counter() - attempt_started) * 1000,
            )

        if attempt < max_retries:
            time.sleep(RETRY_BACKOFF_SECONDS)

    attempts = max_retries + 1
    if isinstance(last_error, requests.ConnectTimeout):
        raise OllamaUnavailableError(model, attempts) from last_error
    if isinstance(last_error, requests.Timeout):
        raise OllamaTimeoutError(
            model,
            OLLAMA_TIMEOUT_SECONDS,
            attempts,
        ) from last_error
    if isinstance(last_error, requests.ConnectionError):
        raise OllamaUnavailableError(model, attempts) from last_error
    raise OllamaCallError(
        f"Ollama request failed after {attempts} attempt(s)."
    ) from last_error


def call_structured_ollama(
    data,
    model,
    schema: type[BaseModel],
    validator=None,
    max_retries=MAX_RETRIES,
):
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = call_ollama(
                data,
                model,
                # The structured wrapper owns retries so schema/parse failures
                # and transport failures share one bounded retry budget.
                max_retries=0,
            )

            content = (
                result
                .get("message", {})
                .get("content", "")
            )

            logger.debug(
                "Ollama structured response model=%s done_reason=%s "
                "output_tokens=%s content_length=%s",
                model,
                result.get("done_reason"),
                result.get("eval_count"),
                len(content),
            )

            if not content or not content.strip():
                raise ValueError(
                    "Ollama returned an empty response."
                )

            parsed = schema.model_validate_json(content)

            if validator is not None:
                validator(parsed)

            return parsed

        except Exception as exc:
            last_error = exc

            # Repeating a slow model request cannot repair a transport timeout
            # and can make the user wait several minutes for the same failure.
            if isinstance(exc, (OllamaTimeoutError, OllamaUnavailableError)):
                raise

            if attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS)

    if isinstance(last_error, OllamaCallError):
        raise last_error
    raise OllamaCallError(
        f"Structured Ollama call failed after {max_retries + 1} attempt(s)."
    ) from last_error


def call_text_ollama(
    data,
    model,
    max_retries=0,
    on_token=None,
):
    payload = data.copy()
    options = payload.get("options")
    options = options.copy() if isinstance(options, dict) else {}
    options.setdefault("num_predict", TEXT_MAX_OUTPUT_TOKENS)
    options.setdefault("num_ctx", TEXT_CONTEXT_TOKENS)
    options.setdefault("temperature", 0.25)
    payload["options"] = options

    if on_token is not None:
        return _call_streaming_text_ollama(
            payload,
            model,
            on_token,
        )

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = call_ollama(
                payload,
                model,
                # Avoid multiplying retries across this wrapper and
                # call_ollama; max_retries here is the total attempt budget.
                max_retries=0,
            )

            content = (
                result
                .get("message", {})
                .get("content", "")
            )

            if not content or not content.strip():
                raise ValueError(
                    "Ollama returned an empty text response."
                )

            return content

        except Exception as exc:
            last_error = exc

            if isinstance(exc, (OllamaTimeoutError, OllamaUnavailableError)):
                raise

            if attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS)

    if isinstance(last_error, OllamaCallError):
        raise last_error
    raise OllamaCallError(
        f"Text Ollama call failed after {max_retries + 1} attempt(s)."
    ) from last_error


def _call_streaming_text_ollama(payload, model, on_token):
    """Stream Ollama text, continuing once if generation hits its token cap."""
    request_payload = payload.copy()
    request_payload["model"] = model
    request_payload["stream"] = True
    started = perf_counter()
    all_chunks = []
    current_payload = request_payload
    continuation_count = 0
    max_continuations = 2
    final_done_reason = None
    final_eval_count = None
    final_needs_continuation = False

    while True:
        response = None
        chunks = []
        done_reason = None
        eval_count = None
        stream_completed = False
        try:
            response = requests.post(
                OLLAMA_URL,
                json=current_payload,
                timeout=(
                    OLLAMA_CONNECT_TIMEOUT_SECONDS,
                    OLLAMA_TIMEOUT_SECONDS,
                ),
                stream=True,
            )
            response.raise_for_status()

            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8")
                try:
                    item = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise OllamaCallError(
                        "Ollama returned an invalid streaming response."
                    ) from exc

                if item.get("error"):
                    raise OllamaCallError(
                        "Ollama could not complete the streaming response."
                    )

                delta = item.get("message", {}).get("content", "")
                if delta:
                    chunks.append(delta)
                    all_chunks.append(delta)
                    on_token(delta)

                if item.get("done"):
                    stream_completed = True
                    done_reason = item.get("done_reason")
                    eval_count = item.get("eval_count")

        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            logger.warning(
                "ollama_stream model=%s outcome=http_error status_code=%s duration_ms=%.1f",
                model,
                status_code,
                (perf_counter() - started) * 1000,
            )
            raise OllamaCallError(
                f"Ollama returned HTTP {status_code or 'error'}."
            ) from exc
        except requests.ConnectTimeout as exc:
            logger.warning(
                "ollama_stream model=%s outcome=connect_timeout duration_ms=%.1f",
                model,
                (perf_counter() - started) * 1000,
            )
            raise OllamaUnavailableError(model, 1) from exc
        except requests.Timeout as exc:
            logger.warning(
                "ollama_stream model=%s outcome=read_timeout duration_ms=%.1f",
                model,
                (perf_counter() - started) * 1000,
            )
            raise OllamaTimeoutError(model, OLLAMA_TIMEOUT_SECONDS, 1) from exc
        except requests.ConnectionError as exc:
            logger.warning(
                "ollama_stream model=%s outcome=connection_error duration_ms=%.1f",
                model,
                (perf_counter() - started) * 1000,
            )
            raise OllamaUnavailableError(model, 1) from exc
        finally:
            if response is not None:
                response.close()

        if not chunks and not all_chunks:
            raise OllamaCallError("Ollama returned an empty text response.")

        final_done_reason = done_reason
        final_eval_count = eval_count
        options = current_payload.get("options") or {}
        try:
            token_limit = int(options.get("num_predict", 0))
            needs_continuation = (
                not stream_completed
                or done_reason == "length"
                or (
                    eval_count is not None
                    and token_limit > 0
                    and int(eval_count) >= token_limit
                )
            )
        except (TypeError, ValueError):
            needs_continuation = not stream_completed or done_reason == "length"
        final_needs_continuation = needs_continuation
        if not needs_continuation or continuation_count >= max_continuations:
            break

        logger.warning(
            "ollama_stream model=%s outcome=continuing reason=%s "
            "continuation=%s eval_count=%s",
            model,
            done_reason or ("missing_done" if not stream_completed else "token_limit"),
            continuation_count + 1,
            eval_count,
        )
        continuation_messages = [
            dict(message)
            for message in (request_payload.get("messages") or [])
        ]
        continuation_messages.extend([
            {"role": "assistant", "content": "".join(all_chunks)},
            {
                "role": "user",
                "content": (
                    "Continue the unfinished answer exactly where it stopped. "
                    "Do not repeat any text already written. Finish the current "
                    "point and answer the remaining request concisely."
                ),
            },
        ])
        current_payload = request_payload.copy()
        current_payload["messages"] = continuation_messages
        continuation_count += 1

    result = "".join(all_chunks)
    if not result.strip():
        raise OllamaCallError("Ollama returned an empty text response.")

    if final_needs_continuation:
        completion_notice = (
            "\n\n*The local model response may be incomplete. Ask me to "
            "continue if you need the remaining details.*"
        )
        result += completion_notice
        on_token(completion_notice)
        logger.error(
            "ollama_stream model=%s outcome=incomplete_after_continuations "
            "done_reason=%s continuations=%s eval_count=%s",
            model,
            final_done_reason,
            continuation_count,
            final_eval_count,
        )
    else:
        logger.info(
            "ollama_stream model=%s outcome=success done_reason=%s "
            "continuations=%s eval_count=%s duration_ms=%.1f output_chars=%s",
            model,
            final_done_reason,
            continuation_count,
            final_eval_count,
            (perf_counter() - started) * 1000,
            len(result),
        )
    return result
