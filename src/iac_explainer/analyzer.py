import json
import time
import anthropic
from dotenv import load_dotenv

from .schemas import Analysis
from .prompts import SYSTEM_PROMPT

load_dotenv()

client = anthropic.Anthropic()

_RETRYABLE = (anthropic.RateLimitError, anthropic.APIStatusError)
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0


class AnalysisError(Exception):
    pass


def analyze(raw_hcl: str, parsed_resources: list[dict]) -> Analysis:
    """Call Claude with forced tool-use to get a schema-conformant Analysis."""
    user_content = (
        f"<terraform>\n{raw_hcl}\n</terraform>\n\n"
        f"<parsed_resources>\n{json.dumps(parsed_resources, indent=2)}\n"
        f"</parsed_resources>\n\n"
        "Analyse this infrastructure and respond with the structured analysis."
    )

    tool_def = {
        "name": "submit_analysis",
        "description": "Submit the structured infrastructure analysis",
        "input_schema": Analysis.model_json_schema(),
    }

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                tools=[tool_def],
                tool_choice={"type": "tool", "name": "submit_analysis"},
            )
            break
        except anthropic.RateLimitError as exc:
            last_exc = exc
            wait = _BACKOFF_BASE ** attempt
            time.sleep(wait)
        except anthropic.AuthenticationError as exc:
            raise AnalysisError(
                "Invalid or missing ANTHROPIC_API_KEY. "
                "Set it in your .env file or as an environment variable."
            ) from exc
        except anthropic.APIStatusError as exc:
            # 529 overloaded — retry; other 4xx are bugs, re-raise immediately
            if exc.status_code == 529:
                last_exc = exc
                time.sleep(_BACKOFF_BASE ** attempt)
            else:
                raise AnalysisError(f"API error {exc.status_code}: {exc.message}") from exc
        except TypeError as exc:
            # Raised by the SDK when no API key is configured at all
            raise AnalysisError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
            ) from exc
    else:
        raise AnalysisError(f"Claude API unavailable after {_MAX_RETRIES} attempts: {last_exc}")

    tool_block = next(
        (b for b in response.content if b.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise AnalysisError(
            "Claude did not return a tool_use block. "
            f"Stop reason: {response.stop_reason}"
        )

    return Analysis.model_validate(tool_block.input)
