# ADR 0001: Require Eluna for playerbots

- Status: accepted
- Date: 2026-08-09

## Context

The AI-player project needs a stable scripting boundary for server events and
future bot-specific social extensions. Supporting bot installations both with
and without Eluna would create two lifecycle paths, two integration surfaces,
and a large testing matrix.

## Decision

Building playerbots requires Eluna. CMake forces `BUILD_ELUNA=ON` when
`BUILD_PLAYERBOTS=ON`. Eluna uses the `ELUNA_VMANGOS` host adapter and Vanilla
expansion setting for compatibility with this Turtle WoW core.

Standard Eluna hooks are integrated first. Custom playerbot Lua methods will be
small, non-blocking, and social-only when introduced.

## Consequences

- Every bot server receives one consistent Lua lifecycle and scripting API.
- Eluna and Lua become build/runtime dependencies for playerbot deployments.
- Eluna pin updates require compatibility builds and lifecycle tests.
- Unsafe Lua methods remain disabled by default.
- The sidecar is still a separate process; Eluna is not the model or memory
  network client.

