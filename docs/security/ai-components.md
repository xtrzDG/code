# Third-party AI agent components

What the assistant is built from outside this repository, how each piece
is pinned, and where the pin lives (AI-12, OWASP LLM03 Supply Chain,
OWASP Agentic ASI04). A pin changes only in a pull request: the eval
replay (`tests/evals/test_replay_cassettes.py`) fails on a changed
instruction or tool list, and `tests/platform/test_model_pins.py` keeps
every default model a pinned version and this list complete.

The platform runs no MCP servers, agent plugins or third-party tools: every
tool the model may call is code in this repository
(`app/use_cases/conversations/tools/`, `AssistantToolName`).

## Language models

Default model ids are pinned versions, never floating aliases
(`app/utilities/conversations/llm_model_pins.py`). Where the provider
publishes a dated snapshot, the default is that snapshot; Claude Opus 5.5
and Claude Sonnet 5.5 are published as fixed model ids without a date and
are not repointed. Every id can be overridden by its environment variable;
an override should name a pinned version too (`.env.example`).

| Use | Default (pinned) | Variable | Provider |
| --- | --- | --- | --- |
| Chat replies, OpenAI deployments | `gpt-5-mini-2025-08-07` | `LLM_MODEL_ID` | OpenAI (EU data residency) |
| Chat replies, Anthropic deployments | `claude-opus-5-5` | `LLM_MODEL_ID` | Anthropic |
| Failover to the other provider | `claude-sonnet-5-5` / `gpt-5-mini-2025-08-07` | `LLM_FALLBACK_MODEL_ID` | Anthropic / OpenAI |
| Autotest customer and judge | `claude-sonnet-5-5` / `gpt-5-mini-2025-08-07` | `LLM_JUDGE_MODEL_ID` | the other provider |
| Claim check of the reply guard | `gpt-5-nano-2025-08-07` / `claude-haiku-4-5-20251001` | `LLM_VERIFIER_MODEL_ID` | the chat's provider |
| Answers past the soft spend limit | `gpt-5-nano-2025-08-07` / `claude-haiku-4-5-20251001` | `SPEND_SOFT_LIMIT_MODEL_ID` | the chat's provider |
| Menu photo and PDF import | `gpt-5-mini-2025-08-07` | (the chat model when it is OpenAI's) | OpenAI |
| Voice note transcription | `gpt-4o-transcribe` | `LLM_TRANSCRIBE_MODEL` | OpenAI |
| Knowledge embeddings | `text-embedding-3-small` | `EMBEDDINGS_MODEL_ID` | OpenAI |
| Development, tests, evals in CI, preview stand | `scripted` | `LLM_PROVIDER=scripted` | none (offline) |

`gpt-4o-transcribe` and `text-embedding-3-small` are published by OpenAI
without a dated snapshot; a change of their behaviour shows in the voice
note and knowledge search tests of the nightly live run.

Each assistant reply stores the model that answered it, whether it was
the fallback, its tool calls with their input and result, and the
assistant version (its instruction text and tools)
(`MessageDocument.model_id`, `tool_calls`, `is_fallback_model`;
`ConversationDocument.assistant_version_id`).

## Voice agent (ElevenLabs Conversational AI)

The voice agent of every business is created and updated by the platform
from code (`app/adapters/voice/elevenlabs_agent_config.py`); its build is
versioned by `VOICE_AGENT_REVISION` (now 3,
`app/utilities/assembly/voice_agents.py`), and `resync_voice_agents` sets
up every live agent of an older revision again.

| Component | Pin | Where |
| --- | --- | --- |
| Agent language model | `gemini-2.5-flash` (Google's stable id, run by ElevenLabs) | `ELEVENLABS_AGENT_LLM`, `app/schemas/configurations/voice_agent_settings.py` |
| Speech synthesis | `eleven_flash_v2_5` (ru, uk, en, it, de), `eleven_v3_conversational` (ka, he, others) | `app/registries/localization/voice_profile_registry.py` |
| Voices | premade library voices Matilda, Sarah, Jessica, Laura by voice id | `app/registries/localization/voice_profile_registry.py` |
| Speech recognition | quality `high`, the business's keywords | `app/adapters/voice/elevenlabs_agent_tuning.py` |
| Temperature and turn timeout | 0.2, 8 s | `ELEVENLABS_AGENT_TEMPERATURE`, `ELEVENLABS_TURN_TIMEOUT_SECONDS` |
| Tools | the platform's webhook tools only, signed | `app/adapters/voice/elevenlabs_agent_config.py` |

## Provider SDKs

Exact versions are locked in `uv.lock` (installed with `--frozen` in CI and
the image); `pyproject.toml` gives the lowest accepted version.

| Package | Locked | Used for |
| --- | --- | --- |
| `openai` | 3.40.0 | chat, transcription, embeddings, menu import |
| `anthropic` | 1.17.0 | chat, judge, claim check |
| `elevenlabs` | 2.74.1 | voice agent set-up and call data |

## Changing a pin

1. Change the id in `llm_model_pins.py` (or the voice registry or
   settings), and the table above.
2. Run the eval suite against the new model:
   `uv run python -m scripts.run_evals --model <id> --judge-model <id>`
   (or the nightly workflow with that model) and compare with its baseline.
3. For the voice agent, raise `VOICE_AGENT_REVISION` so live agents are set
   up again.
