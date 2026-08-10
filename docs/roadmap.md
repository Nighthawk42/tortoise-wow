# Implementation roadmap

## Phase 0: host foundation

Status: implemented and runtime-validated.

- Require Eluna whenever playerbots are built.
- Pin Eluna and embed Lua 5.2.
- Connect world, map, player, XP, and chat lifecycle hooks.
- Default unsafe Lua methods off.
- Compile and link the Eluna-enabled core.
- Document the existing playerbot system and target boundaries.

Exit criteria:

- Eluna-only `mangosd` build passes.
- Playerbot configure proves Eluna cannot be disabled.
- Combined build passes with an installed Boost 1.70+ or the pinned fetched
  Boost 1.91.0 fallback.
- A smoke Lua script observes lifecycle hooks without delaying a world tick.
- The existing databases are backed up and populated with playerbot schema.
- Installed Windows binaries load their DLLs and configs from the organized
  runtime tree.
- `realmd` and `mangosd` remain live after a clean restart, Eluna receives
  world-startup event 14, and the one-account random-bot roster enters the
  world.

## Phase 1: dialogue sidecar vertical slice

Status: in progress. The provider adapter and bounded C++ gateway are built and
contract-tested; live in-game whisper and outage validation remain.

- [x] Scaffold FastAPI service with `/health/*`, `/v1/dialogue`, and
  `/v1/outcomes`.
- [x] Add strict request/response models and contract fixtures.
- [x] Implement one OpenAI-compatible provider adapter and bounded prompt compiler.
- [x] Implement hand-crafted profiles, race/class system archetypes, stable seeded
  materialization, schema validation, and explicit roster bindings.
- [x] Add a bounded C++ gateway worker and response queue.
- [x] Replace the production whisper use of the legacy direct
  `PlayerbotLLMInterface::Generate` path with gateway
  enqueue/result consumption.
- [x] Allow only `chat.text` output.
- [x] Add timeouts, rate limits, cancellation, and structured metrics.

Exit criteria:

- Disconnecting the sidecar has no measurable effect on world updates.
- A bound bot can answer a whisper consistently with its simulated player
  profile.
- A late or malformed response is discarded.
- No provider secret is present in the core configuration or process logs.

## Phase 2: memory reference implementation

- Implement working, episodic, semantic, and relationship models.
- Add a local reference adapter with tenant and privacy filters.
- Ingest only confirmed outcomes.
- Add retention, consolidation, contradiction, export, and complete forget flows.
- Build adapter contract tests and failure-injection tests.

Exit criteria:

- A persona recalls an allowed prior interaction after relogging.
- Whisper content is excluded under the default policy.
- Deletion removes raw records, embeddings, summaries, and caches.
- Memory outage degrades to stateless dialogue.

## Phase 3: MemPalace or broader provider

- Implement a MemPalace adapter and run the shared contract suite.
- Compare operational cost, latency, retrieval quality, deletion guarantees, and
  portability against the reference adapter.
- Select it, another platform, or a hybrid based on measured results.

No core or Eluna API changes are permitted for this phase.

## Phase 4: expanded social behavior

- Add ambient conversations, greetings, rumors, and relationship-sensitive
  responses behind separate policies and rate limits.
- Add operator-curated world lore retrieval.
- Add narrowly scoped Eluna playerbot social bindings if scripts need them.
- Add simulation/load tests for hundreds of bound personas.

Gameplay actions remain deterministic. Any future proposal to let a model choose
gameplay intent requires a separate ADR, threat model, allow-list protocol, and
operator opt-in; it is not part of this roadmap.

## Work items that should remain independent

- Provider adapters do not know MaNGOS types.
- Memory adapters do not construct prompts.
- Persona definitions do not store secrets or live character identifiers.
- Roster bindings do not alter character database rows.
- Eluna scripts do not perform external network I/O.
- Core gateway code does not parse provider-specific responses.
