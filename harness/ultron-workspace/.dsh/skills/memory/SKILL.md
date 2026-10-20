---
name: memory
description: Recall and manage user-approved long-term Ultron memories across sessions through a local SQLite CLI.
---
# Ultron Memory Engine V0.6

Runtime: official DeepSeek Harness. Memory engine: `python3 ../memory/cli.py`, relative to the selected `harness/ultron-workspace` workspace. No service, API calls, embeddings, or external database are required.

## Recall (before relevant responses)

When the user's request is affected by preferences, a past project decision, or another approved fact, search first:

```bash
python3 ../memory/cli.py search "query keywords" --limit 8
```

Use only returned approved records as durable facts. Zero matches means **unknown**, not proof of absence. Search is lexical (substring/token matching), not semantic. Do not search for secrets. If a record conflicts with current user instructions, prefer the current user message and propose a correction.

## Saving: proposal and explicit consent

Never directly insert/update/delete SQLite rows or modify the database with external sqlite tools. For adding a memory:

```bash
python3 ../memory/cli.py propose --action add --category preference --scope global --source "user explicitly said ..." --text "Prefers concise Chinese technical answers."
```

Present the *exact content* and the returned `proposal_id` to the user. **Do not approve until the user explicitly consents to this specific proposal**. On consent only:

```bash
python3 ../memory/cli.py approve --proposal-id ID
```

Use `reject` for denied proposals. Read the updated entry with `list` or `search` and report verified result.

## Correction and deletion

First run `list`, identify the approved record's `id`; stage `propose --action update --id MEMORY_ID --text "replacement"` or `propose --action forget --id MEMORY_ID`; show the exact target and ask for confirmation. Only then approve the proposal ID. Never treat an agent's inference as confirmation.

## Boundaries

- Remember only stable, helpful, non-sensitive facts that the user wants saved. Do not automatically extract memories from chat history.
- Do not store API keys, passwords, tokens, credentials or personal high-risk details.
- If a detail should be temporary, keep it in the current Session, not long-term memory.
- Persistent DB is `$DSH_HOME/memory/ultron.sqlite3` (default `~/.ultron-dsh/memory/`), outside Git; **never commit it**.
- Existing `memory/approved.md` is a legacy starter file, not auto-imported. SQLite records are the V0.6 source of truth.
- This is text search, not auto-RAG, embeddings, or an autonomous memory consolidation engine.
- Explicit local filesystem write permissions may be requested by dsh sandbox. Do not bypass permission checks.
