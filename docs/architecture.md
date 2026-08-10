# Target sidecar architecture

## Goals

The system should support dozens or hundreds of distinct players, run against a
cloud or self-hosted LLM, preserve memories across sessions, and remain safe
when every external service is slow or unavailable.

The design separates deterministic gameplay from nondeterministic player-like
conversation and social behavior:

```text
MaNGOS + playerbots + Eluna
  | immutable social event
  v
bounded core gateway queue -> gateway I/O worker
  | versioned HTTPS/HTTP JSON
  v
AI sidecar
  |- persona registry (YAML + roster bindings)
  |- policy and prompt assembly
  |- memory service + provider adapters
  |- model provider adapters
  |- output validation and observability
  |
  v
bounded response queue -> validated playerbot social action
```

## Trust boundaries

The core is the source of truth for identity, location, group membership,
guild membership, visibility, chat permissions, and game state. Event payloads
contain snapshots, not mutable handles.

The sidecar is trusted to propose text. It is not trusted to assert facts about
the live world or to authorize an action. Every returned candidate is treated
as untrusted input and is length checked, encoding checked, policy filtered,
and revalidated in current core context.

The LLM provider sees only the minimum prompt needed for a request. It receives
opaque actor IDs by default, not account names, IP addresses, email addresses,
session tokens, database IDs, or unredacted private chat history.

## Components

### Core gateway

The gateway is compiled with playerbots and exposes a narrow C++ interface:

```cpp
bool TrySubmit(PlayerbotDialogueRequest request);
bool TryTake(std::uint32_t botGuid, PlayerbotDialogueResponse& response);
void ReportOutcome(std::string const& requestId,
                   std::string const& outcome,
                   std::string const& reason);
```

`TrySubmit` is non-blocking. It either copies a bounded snapshot
into the queue or declines it. Network calls happen only on gateway workers.
The response and outcome queues are also bounded, with per-bot pending limits
and per bot/player cooldowns. See [C++ dialogue gateway](core-gateway.md).

Custom Eluna bindings may publish a supported social event or inspect delivery
status, but they call this same gateway. Lua is not given a general HTTP client,
provider key, memory database connection, or arbitrary playerbot action runner.

### Sidecar service

The initial implementation should be Python with FastAPI and Pydantic because
it makes provider adapters, JSON schema validation, YAML tooling, and async I/O
straightforward. The wire contract is language-neutral, so the service can be
replaced later.

Recommended internal modules:

```text
app/
  api/          versioned routes and authentication
  personas/     YAML loading, inheritance, validation, roster binding
  policies/     privacy, channel, rate, and output policy
  prompts/      deterministic profile compilation and prompt assembly
  providers/    OpenAI-compatible and later provider adapters
  memory/       service plus local, MemPalace, and future adapters
  models/       API and domain schemas
  telemetry/    structured logs, metrics, traces, audit records
```

### Model providers

The first provider interface targets OpenAI-compatible chat completions. This
covers many cloud services and self-hosted servers without putting their wire
formats into the core.

Provider configuration belongs in sidecar environment variables or a secret
store. Persona YAML selects a logical model profile such as `dialogue-small`;
it never contains an API key or provider base URL.

The provider receives one compiled player profile per request, never the YAML
registry or raw profile document. Static compiled profiles are revision-keyed
and cached. Fields such as temperature are model API parameters, while timing,
privacy, channel, and memory policy remain outside the prompt.

### Memory providers

The sidecar owns memory ingestion and retrieval. The stable interface is
documented in [memory-system.md](memory-system.md). A local relational/vector
implementation should be the reference adapter. MemPalace can be integrated as
an optional adapter after its retention, deletion, tenancy, and query behavior
passes the same contract tests.

## Request lifecycle

1. Core code observes an eligible social event.
2. Core policy checks channel, rate, privacy scope, and whether this bot has a
   persona binding.
3. A small immutable snapshot receives a UUID correlation ID and deadline.
4. The gateway enqueues it without waiting.
5. A worker calls the sidecar API with service authentication.
6. The sidecar loads the persona and allowed memories, constructs the prompt,
   calls a provider, and validates its response.
7. The worker rejects responses that are late, oversized, malformed, or for a
   different server/persona/request.
8. On a core-owned update, a social action rechecks the bot and channel before
   emitting the text.
9. The sidecar records only policy-approved memories after the outcome event.

## Backpressure and deadlines

The gateway must have global and per-bot queue limits. When full, new low-value
ambient events are dropped first. Player-directed whispers may have higher
priority, but they still have a strict limit.

Suggested starting budgets:

| Budget | Initial value |
| --- | --- |
| Core enqueue time | less than 1 ms, no blocking |
| Dialogue deadline | 8 seconds |
| Maximum pending per bot | 1 |
| Maximum returned text | 255 UTF-8 bytes before game encoding conversion |
| Ambient cooldown | 60 seconds per bot |
| Player-directed cooldown | 5 seconds per bot/player pair |

These are configuration defaults, not protocol guarantees. Load testing should
set final values.

## Failure modes

| Failure | Required result |
| --- | --- |
| Sidecar unavailable | Drop request; deterministic bot AI continues |
| Provider unavailable or rate limited | Sidecar returns typed failure; no core retry loop |
| Memory unavailable | Generate without long-term memory or return typed failure according to policy |
| Invalid persona | Disable that binding and report a validation error |
| Queue full | Drop according to priority; increment metric |
| Late response | Discard by correlation ID/deadline |
| Bot logged out or moved context | Discard during final validation |
| Unsafe or invalid output | Discard; never reinterpret as a command |

## Security baseline

- Bind development sidecars to loopback by default.
- Use TLS and service authentication across hosts.
- Rotate secrets without rebuilding the core.
- Do not log prompts or responses by default; structured metadata is enough.
- Redact player-provided secrets and personally identifying data before storage.
- Give each realm/server a tenant ID and enforce it in every memory query.
- Keep Eluna unsafe methods disabled in production.
- Treat persona files as reviewed code: validate them before activation and
  record their content digest in request audit metadata.
