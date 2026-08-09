# YAML player personality system

## What a personality represents

A personality represents a simulated **player**, not an NPC and not an
in-world quest character. Its purpose is to make a playerbot behave socially
like a consistent person behind a keyboard: it has play preferences, imperfect
game knowledge, habits, goals, communication quirks, friends, and memories.

Authenticity should come from consistent behavior and believable limitations,
not a lore-heavy biography or a collection of scripted catchphrases. Most real
players do not introduce themselves with an occupation, speak only in Warcraft
idioms, or know every fact about the zone they are standing in.

The v1 LLM integration uses this profile for dialogue and social context only.
The existing playerbot engines remain authoritative for combat, movement,
inventory, progression, and other gameplay. Later, selected structured fields
may inform deterministic bot strategies through an explicit allow-listed
mapping; the model itself never issues gameplay commands.

## Player identity versus character identity

The simulated player and the character are separate concepts:

- **player profile**: stable habits, skill, social style, goals, and memories;
- **character binding**: the realm character currently representing that player;
- **character overlay**: optional preferences specific to one alt, such as role,
  current goals, or how seriously the player treats that character.

One player profile may be bound to several alts. This allows the same simulated
player to recognize friends across characters and retain consistent habits. A
deployment may instead enforce one profile per character for simpler operation.

`persona_id` remains the API field name, but it identifies a player profile—not
an NPC role.

## Profile types

The first schema version supports two sources of player personalities.

### 1. Hand-crafted players

Hand-crafted profiles are written deliberately by a server owner or user. They
are the most detailed type and may specify the player's individual habits,
goals, knowledge, communication style, relationships, preferred content,
character overlays, and memory rules.

Their authored fields are stable. The LLM can vary the wording of a response,
but it must not improvise a different background, skill level, temperament, or
set of long-term goals. Hand-crafted profiles should generally use a moderate
temperature so their voice remains recognizable.

### 2. System race/class archetypes

System archetypes provide scalable defaults for valid race/class combinations,
such as a human mage, dwarf warrior, or night elf druid. These are profiles for
the kinds of **players** commonly attracted to that gameplay combination, not
instructions to act like racial NPC stereotypes.

An archetype may influence likely gameplay experience, role familiarity,
content preferences, willingness to group, mechanical vocabulary, and common
goals. Race may provide light context about starting zones and faction; it
must not force accents, catchphrases, or lore-roleplay behavior.

When an unassigned bot first needs a personality, the system:

1. selects the matching race/class archetype;
2. uses a stable random seed to vary traits within declared ranges;
3. chooses bounded communication and model-temperature values;
4. materializes a complete player profile with its own ID;
5. persists that profile and roster binding for future sessions.

The resulting bot is no longer rerolled on every login or request. The
archetype is a factory for consistent individuals, not a prompt shared verbatim
by every bot of the same race and class.

Temperature controls variation in LLM phrasing; it does not replace a
personality. Goals, traits, knowledge limits, memories, and the stable variation
seed provide continuity. The sidecar clamps all requested temperatures to the
selected model profile's safe range.

## Design rules

Profiles are data, not code. They must not contain Lua, SQL, Jinja, shell
fragments, provider credentials, or arbitrary sidecar imports.

Every profile has a stable ID and schema version. Character names can change
and therefore are not profile keys. Roster bindings connect live characters to
profiles.

Loading is atomic: validate all changed files and inheritance references, then
activate the complete registry. A bad file leaves the last known-good registry
active.

## How a profile reaches the LLM

The YAML registry is configuration for the sidecar. It is not pasted into the
model context. For each dialogue request, the sidecar resolves one bot's
`persona_id`, applies its character overlay, retrieves a small amount of
relevant memory, and compiles a compact prompt for that player only.

```text
thousands of YAML profiles loaded by sidecar
                 |
incoming request names one persona_id
                 |
resolve one normalized profile + current character overlay
                 |
prompt compiler selects model-relevant traits
                 |
one compact player instruction + relevant memories + current message
                 |
LLM request
```

An idle profile consumes no model tokens. Having 5,000 profiles in the registry
does not send 5,000 profiles to the LLM; it is comparable to having 5,000 user
records in a database while serving one signed-in user.

### Settings have different destinations

Not every YAML field is an instruction for the model:

| Setting type | Destination |
| --- | --- |
| Voice, knowledge level, conversational temperament, current goals | Compiled into a short player instruction |
| Temperature, maximum output tokens, provider/model selection | Sent as model API parameters |
| Response cadence, typing delay, channel permissions, rate limits | Enforced by the sidecar or core; never shown to the model |
| Memory retention, privacy scope, sharing across alts | Used by the memory service; never shown to the model |
| Roster GUID, server ID, stable seed, source revision | Used for lookup/audit; never shown to the model |
| Gameplay preferences relevant to conversation | Summarized into natural language only when useful |
| Live location, group, speaker, and recent event | Supplied from the current core event, not treated as personality |

Numeric traits are also not dumped as a list of floating-point values. A
deterministic prompt compiler turns them into a small number of non-conflicting
behavioral instructions. For example:

```text
You are simulating Mirae, a regular but casual player controlling this
character. Mirae has played before but is rusty and does not pretend to know
every mechanic. She prefers questing and small dungeons, is patient and fairly
helpful, but rarely leads groups. Write brief, casual messages, usually in
lowercase, with light punctuation. Use common game terms naturally. It is fine
to be uncertain, not answer, or ask another player. Current goals: finish the
Westfall quests, improve leatherworking, and save for a mount. Never invent
real-world personal details or claim events that were not provided.
```

The actual provider call is assembled in layers:

```text
system: global safety and output contract
system: compiled player profile
system: relevant, privacy-approved memories and observed facts
user:   the current chat/event snapshot

API parameters: model, temperature, token limit, deadline
```

The model is effectively stateless between calls. Consistency comes from using
the same compiled profile revision and retrieving relevant memories on every
request, not from assuming the provider remembers a previous conversation.

### Prompt budget and caching

The compiler applies a token budget and prioritizes identity-defining settings.
A reasonable initial target is:

| Prompt section | Target budget |
| --- | ---: |
| Global safety/output contract | 150–300 tokens |
| Compiled player profile | 200–500 tokens |
| Retrieved memories | 200–600 tokens |
| Recent conversation and current event | 300–1,000 tokens |

These are ceilings to tune through evaluation, not guaranteed allocations. The
compiler drops low-priority flavor before stable behavior or safety rules.

The sidecar caches compiled profiles by `(persona_id, profile_revision,
character_overlay_revision, compiler_version)`. A profile is recompiled only
when one of those inputs changes. Providers that support prompt-prefix caching
can also reuse the global instructions, while the individual player block stays
small.

At runtime, cost and capacity depend on active dialogue requests, not total
registered players. Bounded queues, per-player cooldowns, ambient-chat limits,
and provider concurrency caps prevent thousands of profiles from becoming
thousands of simultaneous generations.

## Proposed player profile schema

```yaml
schema_version: 1
kind: player_profile
id: players.mirae
extends:
  - archetypes.social_leveler

provenance:
  type: handcrafted
  authored_by: operator

identity:
  handle: mirae
  presentation: returning_player
  player_since: vanilla
  real_world_details: never_invent

gameplay:
  experience: 0.68
  mechanical_skill: 0.56
  game_knowledge: 0.62
  confidence: 0.48
  risk_tolerance: 0.40
  patience: 0.78
  efficiency_vs_exploration: 0.42
  preferred_content:
    - questing
    - small_dungeons
    - professions
  avoids:
    - speedrunning
    - unsolicited_pvp
  roles:
    preferred:
      - damage
    willing:
      - healing
  mistakes:
    misses_mechanics_chance: 0.08
    asks_when_uncertain: true
    admits_not_knowing: true

activity:
  style: regular_casual
  typical_session_minutes:
    min: 35
    max: 150
  break_frequency: occasional
  afk_style: announces_in_group
  repeat_content_tolerance: 0.45

goals:
  current:
    - finish the Westfall quest lines
    - save for a mount
    - level skinning and leatherworking
  long_term:
    - see every classic dungeon at least once
  persistence: 0.72
  changes_mind_chance: 0.10

communication:
  register: casual
  message_length: short
  capitalization: mostly_lowercase
  punctuation: light
  typo_rate: 0.025
  correction_rate: 0.35
  abbreviations:
    frequency: occasional
    examples:
      - brb
      - omw
      - ty
  emotes: rare
  humor: dry
  response_cadence:
    minimum_delay_ms: 900
    reading_ms_per_character: 35
    sometimes_does_not_reply: true
  avoids:
    - lore monologues
    - repeating the other person's message
    - claiming perfect knowledge
    - modern meme spam

social:
  sociability: 0.66
  helpfulness: 0.74
  group_initiative: 0.38
  leadership: 0.24
  competitiveness: 0.30
  stranger_trust: 0.32
  conflict_style: quiet_deescalation
  loot_attitude: ask_when_unclear
  group_exit_style: says_goodbye
  channels:
    whisper: true
    say: true
    party: true
    guild: true
    world: false

knowledge:
  game_era: vanilla
  perspective: experienced_but_rusty
  knows_game_terms: true
  discusses_mechanics: naturally
  allows_uncertainty: true
  spoiler_behavior: avoids_unprompted
  forbidden:
    - future expansion knowledge
    - server administration secrets
    - private information about other players

model:
  profile: dialogue-small
  temperature: 0.68

memory:
  profile: social-default
  share_across_bound_alts: true
  remember_player_names: true
  remember_shared_runs: true
  remember_favors_and_promises: true
  remember_private_chat_content: false
  relationship_scope: persona_actor
  episodic_ttl_days: 90

safety:
  never_invent_real_world_identity: true
  never_claim_offline_contact: true
  refuse_personal_data_requests: true
  refuse_admin_impersonation: true
  never_claim_unobserved_gameplay: true
```

Numeric traits range from `0.0` to `1.0`. They are stable tendencies, not rigid
rules and not probabilities unless the field explicitly ends in `_chance`.
Free-text fields and lists have strict length limits.

## What makes a bot feel player-like

A believable profile needs variation in more than prose style:

- It does not answer every message.
- It takes time to read and type instead of replying instantly.
- It sometimes knows a mechanic, sometimes remembers only part of it, and can
  comfortably say it is unsure.
- It has recurring goals across sessions instead of treating every event as an
  isolated prompt.
- It develops familiarity with players after shared groups and conversations.
- It uses game terminology naturally without delivering encyclopedia entries.
- It has preferences that occasionally produce inefficient but plausible play.
- It reacts consistently to wipes, loot disputes, invitations, help, and long
  periods of silence.
- It does not turn every line into theatrical roleplay.

Imperfection must be bounded. The system may simulate hesitation, incomplete
knowledge, typos, or a change of mind; it must not deliberately grief groups,
misuse loot, leak private information, or sabotage gameplay.

## Activity and session behavior

The `activity` section describes a player's tendencies. It does not directly
schedule logins from the LLM. `RandomPlayerbotMgr` remains responsible for
population, login, logout, and performance limits.

A future deterministic adapter may translate an activity profile into bounded
manager settings such as preferred session duration or likelihood of joining a
group. That mapping must be implemented and tested in core code. Profile text
cannot override server population policy.

## Communication behavior

The sidecar should derive wording and response timing from structured fields,
not paste every field into the prompt verbatim. Typing simulation happens after
generation and before core delivery:

1. Generate a short semantic response.
2. Apply profile-specific formatting within safe bounds.
3. Calculate a delivery delay from message length and cadence.
4. Revalidate the current channel and conversation before sending.

Typos should be rare and subtle. Artificially misspelling every sentence is
more conspicuous than clean text. Catchphrases and fixed idiom lists should also
be uncommon because repetition quickly exposes automation.

## Knowledge and uncertainty

Player knowledge is not the same as character knowledge. A player profile may
understand aggro, talent builds, dungeon routes, addons, or loot etiquette even
when the character would not know those as lore concepts.

Knowledge has three sources:

- the stable profile's general game literacy;
- operator-curated, era-correct server knowledge;
- events and memories the simulated player has actually observed.

The sidecar must distinguish `does not know`, `might remember`, and `knows`.
Retrieval failure should produce uncertainty, not invented expertise.

## Inheritance and archetypes

`extends` references other documents by ID. The loader resolves parents left to
right, then applies the child. Maps merge recursively; scalars replace; lists
replace unless the schema explicitly marks a list as additive.

Useful archetypes are player patterns such as:

- social leveler;
- quiet gatherer;
- dungeon regular;
- competitive battleground player;
- completionist;
- new player learning the game;
- experienced player leveling an alt.

Archetypes provide starting values, not finished personalities. Each deployed
profile should vary its goals, knowledge, communication, social tendencies, and
history. Inheritance depth is limited and cycles are validation errors.

### Race/class archetype example

System archetypes contain ranges or weighted choices that are resolved once
when an individual profile is materialized:

```yaml
schema_version: 1
kind: player_archetype
id: archetypes.human.mage

selection:
  race: human
  class: mage

generation:
  profile_id_prefix: generated.human.mage
  stable_seed_required: true
  traits:
    experience: { min: 0.25, max: 0.85 }
    mechanical_skill: { min: 0.30, max: 0.82 }
    sociability: { min: 0.25, max: 0.80 }
    risk_tolerance: { min: 0.20, max: 0.65 }
  weighted_preferences:
    - value: questing
      weight: 5
    - value: dungeons
      weight: 4
    - value: professions
      weight: 2
    - value: battlegrounds
      weight: 1
  communication_styles:
    - value: quiet_and_direct
      weight: 3
    - value: friendly_casual
      weight: 5
    - value: analytical
      weight: 2
  model:
    profile: dialogue-small
    temperature:
      min: 0.60
      max: 0.88
```

The materialized profile records `provenance.type: system_archetype`, the source
archetype ID, its revision, and the stable seed. It stores concrete values—not
ranges—so behavior remains reproducible after a restart or archetype update.
Existing generated players do not silently change when their source archetype
is edited; migration is an explicit administrative operation.

## Roster bindings and alts

Roster YAML is deployed separately because it binds simulated identities to
live server characters.

```yaml
schema_version: 1
server_id: turtle-dev
realm_id: 1
bindings:
  - character_guid_low: 4821
    expected_character_name: Mirae
    persona_id: players.mirae
    enabled: true
    character_overlay:
      status: main
      current_role: damage
      seriousness: 0.65

  - character_guid_low: 9377
    expected_character_name: Miralen
    persona_id: players.mirae
    enabled: true
    character_overlay:
      status: alt
      current_role: healing
      seriousness: 0.35
```

The stable character key is `(server_id, realm_id, character_guid_low)`. The
expected name catches copied databases and mistaken realm configuration. A
binding is disabled if the live name differs.

The simulated player ID is independent from the actual account table. The
sidecar does not need account credentials or login-database IDs. Multiple
bindings may share a player profile only when explicitly configured.

Generated populations select the valid race/class archetype first, then may
combine it with a compatible general player pattern such as `social_leveler` or
`quiet_gatherer`. The resulting concrete player profile must be materialized and
persisted. A bot must not receive a new personality, skill level, temperature,
or social history every time it logs in.

## Model profiles

`model.profile` is a logical name resolved by sidecar configuration. It defines
the default temperature and a range that both hand-crafted and system-generated
profiles must obey:

```yaml
model_profiles:
  dialogue-small:
    provider: local-openai-compatible
    model: qwen-dialogue
    temperature:
      default: 0.70
      min: 0.45
      max: 0.95
    max_output_tokens: 80
    timeout_seconds: 6
```

The player profile contains only the logical name. Provider endpoints and API
keys stay in sidecar secrets, allowing hundreds of profiles to move between
cloud and self-hosted providers without rewriting personality files.

The optional concrete `model.temperature` value is passed to providers that
support it after clamping. For providers without a temperature parameter, the
adapter ignores it and reports that capability in diagnostics. Temperature may
vary prose, humor, and word choice, but output validation and the player's
stable behavioral fields always take precedence.

## Validation

The loader rejects:

- unknown schema versions, profile/archetype kinds, or duplicate IDs;
- unknown fields unless explicitly allowed in development;
- inheritance cycles or missing parents;
- numeric values outside declared ranges;
- excessive strings, lists, or inheritance depth;
- duplicate character bindings;
- missing model or memory profiles, or temperatures outside the model profile's
  allowed range;
- race/class archetypes for combinations the core does not permit;
- generated profiles without a stable seed, source revision, or concrete
  materialized values;
- roster entries whose overlays violate the player-profile schema;
- templating syntax or prohibited control characters;
- fields that request invented real-world identities or external contact data.

CI validates all profiles and bindings, produces a normalized registry, and
reports its SHA-256 digest. Requests record the active registry digest and
individual profile revision in audit metadata.

## Scaling to hundreds of simulated players

Keep archetypes shallow, materialize assigned profiles, and cache normalized
immutable data. Variation should be generated once and reviewed or validated,
not randomized on each prompt. Resolve roster bindings in constant time and
load relationship memory on demand.

Population quality should be evaluated statistically: distribution of skill,
content preferences, response rates, session patterns, group roles, verbosity,
and social initiative. A hundred profiles with different names but identical
behavior are still one obvious bot repeated a hundred times.
