# Sidecar API contract

## Conventions

The API is versioned under `/v1`. Requests use UTF-8 JSON. Every request carries
a unique `request_id`, stable `server_id`, absolute deadline, and contract
version. The current strict models reject unknown fields, missing required
fields, and unknown enum values.

The core's gateway worker is the HTTP client. The world and map update threads
never perform HTTP.

Authentication should use a bearer service token for the first loopback/LAN
deployment, with mTLS available for multi-host production deployments. Provider
credentials are never sent by the core.

## Health endpoints

### `GET /health/live`

Returns success when the process can serve requests.

### `GET /health/ready`

Returns success only when configuration, active persona files, roster bindings,
and required provider adapters have loaded. Optional memory-provider degradation
is included in the body.

## Dialogue endpoint

### `POST /v1/dialogue`

This endpoint may be synchronous from the gateway worker's perspective, but is
always asynchronous from the game loop's perspective.

Example request:

```json
{
  "contract_version": "1.0",
  "request_id": "5f7e4dd5-f4e4-4c7a-85cf-9e31bbbaeeec",
  "server_id": "turtle-dev",
  "realm_id": 1,
  "deadline": "2026-08-09T18:30:08Z",
  "event": {
    "type": "dialogue.requested",
    "occurred_at": "2026-08-09T18:30:00Z",
    "channel": "whisper",
    "text": "Do you know the way to Sentinel Hill?",
    "language": "common"
  },
  "bot": {
    "actor_id": "realm:1:character:4821",
    "character_guid_low": 4821,
    "name": "Mirae",
    "level": 18,
    "race": "human",
    "class": "hunter",
    "zone": "Westfall",
    "subzone": "The Jansen Stead",
    "group_role": "damage"
  },
  "speaker": {
    "actor_id": "session:01J4K8FQ7P7GQYAC9H8J5M5A0F",
    "display_name": "Traveler",
    "kind": "player",
    "relationship": "stranger"
  },
  "limits": {
    "max_utf8_bytes": 255,
    "allowed_output": ["chat.text"]
  },
  "context": {
    "recent_dialogue": [],
    "facts": ["Sentinel Hill is southeast of the Jansen Stead"]
  }
}
```

The core does not need to know a persona ID. The sidecar resolves the binding
from `server_id`, `realm_id`, and `character_guid_low`; an optional `persona_id`
may be supplied only as an additional consistency assertion.

Successful response:

```json
{
  "contract_version": "1.0",
  "request_id": "5f7e4dd5-f4e4-4c7a-85cf-9e31bbbaeeec",
  "status": "completed",
  "candidate": {
    "type": "chat.text",
    "text": "yeah, follow the road southeast from here. omw that way too",
    "language": "common"
  },
  "persona": {
    "id": "players.mirae",
    "revision": "sha256:9d30..."
  },
  "memory": {
    "retrieval_count": 2,
    "write_proposals": 0
  }
}
```

Typed failure response:

```json
{
  "contract_version": "1.0",
  "request_id": "5f7e4dd5-f4e4-4c7a-85cf-9e31bbbaeeec",
  "status": "failed",
  "error": {
    "code": "provider_timeout",
    "retryable": true
  }
}
```

The core does not retry automatically. A later player event may create a new
request with a new ID.

## Outcome endpoint

### `POST /v1/outcomes`

After the core emits or rejects a candidate, the gateway sends an outcome. This
prevents the sidecar from treating proposed text as something that actually
happened.

```json
{
  "contract_version": "1.0",
  "request_id": "5f7e4dd5-f4e4-4c7a-85cf-9e31bbbaeeec",
  "server_id": "turtle-dev",
  "occurred_at": "2026-08-09T18:30:03Z",
  "outcome": "emitted",
  "reason": null
}
```

Allowed initial outcomes are `emitted`, `expired`, `context_changed`,
`policy_rejected`, and `bot_unavailable`.

## Administrative endpoints

Administrative endpoints must use a distinct credential and should not be
reachable from the public internet.

- `POST /v1/admin/reload` atomically reloads and validates YAML files.
- `GET /v1/admin/personas` reports active IDs, revisions, and validation state.
- `GET /v1/admin/bindings` reports roster resolution without exposing account
  credentials.
- `POST /v1/admin/memory/forget` performs an audited deletion by tenant,
  persona, actor, scope, or retention cutoff.

## Idempotency and ordering

The sidecar stores a short-lived idempotency record by `(server_id, request_id)`.
Duplicate dialogue requests return the same completed response when available.
Events from different bots are unordered. Events for one bot carry an optional
monotonic `bot_sequence`; the sidecar must not use it as a security boundary.

## Error codes

Initial stable codes are `invalid_request`, `deadline_expired`,
`persona_not_found`, `persona_invalid`, `policy_denied`, `rate_limited`,
`provider_unavailable`, `provider_timeout`, `provider_invalid_output`,
`memory_unavailable`, and `internal_error`.

The response never contains a stack trace, provider secret, raw provider body,
or executable command.
