# Contacts and Discussions Architecture

This module is the long-running conversation workspace for Apmatia.
It is intentionally not a ChatGPT-style session manager.

## Purpose

The goal is to preserve a single growing discussion per agent or group while
keeping the work usable through topic boundaries.

Think of it like Microsoft Teams with durable history:

- one conversation stream per chat target
- topic breaks inside that stream
- older topics collapsed by default
- topic summaries available for fast context recovery
- agents able to mine the full history later for durable context

## Core Concepts

- `Agent` or `Group`: the chat target
- `Discussion`: the always-on conversation stream with that target
- `Topic`: a collapsible segment of the discussion with a title and context
- `Turn`: an individual message or tool-mediated step inside a topic
- `Summary`: a compact artifact that can be attached to a topic for later reuse

## Product Rules

- Do not model conversations as a large list of independent sessions.
- Do not require manual `Discussion ID` entry in the UI.
- Selecting a target should be enough to resume or begin chatting.
- Topics exist to keep long histories navigable, not to replace the discussion.
- The UI should help the user switch targets, not manage a database of chats.

## Intended UI Shape

### Discussion View

This should be the primary chat surface.

Expected behavior:

- show the current active discussion
- display the currently expanded topic at the top of the working area
- allow typing and sending messages directly
- allow hard topic breaks when the subject changes
- show older topics collapsed below the active context

### Chat Targets

This should be the target picker, not a CRUD-style participant table.

Expected behavior:

- search and select an agent or group
- resume an existing target thread when selected
- create a new group from the same surface when needed
- allow per-target model alias selection
- allow tool restrictions as a multi-select checklist
- show turn policy only for group-style chats

### Discussions / History

This should act as a browsing and resumption surface.

Expected behavior:

- list recent active targets first
- show older targets and topic history underneath
- make old discussions easy to reopen
- keep the list lightweight and resumable

### Topic Summaries

This should only be populated after chat targets are selected.

Expected behavior:

- require a valid chat target first
- build summaries from the discussion history already in context
- support summarization when a topic closes or evolves

### Discussion Turns

This is the actual message log.

Expected behavior:

- store message order and speaker metadata
- support tool events and system turns
- remain subordinate to the discussion/topic structure

## Desired Interaction Flow

1. User selects an agent or group in `Chat Targets`.
2. The target becomes the active discussion.
3. The chat view opens immediately.
4. The user chats until the topic changes.
5. The user hard-splits or organically advances to a new topic.
6. The previous topic collapses into history.
7. Older topics remain available and can be re-expanded later.

## Data and Metadata Expectations

- Every object should inherit Apmatia ownership and mode metadata from the shared core model layer.
- Group and agent names should follow the same uniqueness and validation rules used elsewhere in Apmatia.
- Selected model references should use human-friendly aliases in the UI.
- Tool restrictions should be selectable as a list of multiple tools to deny together.

## Non-Goals

- No separate session list like ChatGPT.
- No mandatory discussion ID entry.
- No generic CRUD-first UI for the human chat workflow.
- No need to expose every underlying database field in the primary user flow.

## Notes For Future Work

- The discussion view should eventually become the main conversation surface.
- Participant selection should probably be a search-driven chooser rather than a table.
- Topic expansion/collapse state should remain easy to scan and easy to resume.
- Agents may later extract durable memory from the same preserved history.
