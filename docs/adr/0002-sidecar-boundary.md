# ADR 0002: Sidecar owns model and memory access

- Status: accepted
- Date: 2026-08-09

## Context

The imported playerbot code contains legacy direct LLM endpoint configuration
and an `ai chat` strategy. Provider calls have unpredictable latency, secrets,
protocol differences, and failure modes. Long-term memory adds its own storage,
privacy, retention, and retrieval concerns.

Putting these concerns in the game process risks world-tick stalls and couples
the core to rapidly changing external services.

## Decision

A separate API sidecar owns:

- model provider configuration and credentials;
- YAML persona loading and roster resolution;
- prompt construction and output policy;
- all memory ingestion, retrieval, consolidation, and deletion;
- provider-specific retry and observability behavior.

The core communicates through bounded queues and a dedicated I/O worker. The
LLM can propose dialogue text only in v1. The core validates current state and
is always authoritative.

MemPalace may be implemented as a memory adapter, but it is not part of the
core-side contract.

## Consequences

- External failures degrade to deterministic bot behavior or silence.
- Provider changes do not require rebuilding the server.
- Memory policy can be tested and audited independently.
- An extra process must be deployed and monitored.
- The gateway and API contract require careful versioning and backpressure.

