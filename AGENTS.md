# AeroPatch — model routing

## Layout

| Role | Agent | Model | Cost |
| --- | --- | --- | --- |
| Lead | main session | `opencode/deepseek-v4.1-flash-free` | free |
| Swarm | `search` | `opencode/glm-5.3-flash-free` | free |
| Swarm | `grep` | `opencode/glm-5.3-flash-free` | free |
| Swarm | `audit` | `opencode/mimo-v2.6-flash-free` | free |
| Advisor | `advisor` | `opencode/beam-free` | free |

All free tiers come from the `opencode` provider — no OpenRouter credits are
spent. Roles are spread across three different models on purpose: a single
free-tier rate limit then stalls at most one role instead of the whole swarm.
Break a task into fewer, larger delegations, because each one is a separate
rate-limited call.

## Delegation rules

- Delegate repo mapping to `search` and symbol/call-site lookups to `grep`.
  Do not run broad `rg` or glob sweeps in the main context.
- Delegate diff review to `audit` before reporting work as done.
- Do not delegate a single file read or a one-line targeted lookup. The handoff
  costs more than it saves.
- Never work around a subagent's read-only permissions. If a subagent needs to
  change something, it reports back and the main session makes the edit.

## Advisor triggers

Call `advisor` when, and only when:

1. A plan is about to be locked and the change touches more than one file, adds
   a module, or changes a schema, config key, or public interface.
2. The same error appears twice in a row.
3. Work is about to be declared complete.

Skip `advisor` on routine turns. It cannot edit files or run commands.

## Constraints

- `audit` runs read-only: `edit` denied, `bash` limited to `git diff`, `git
  status`, `git log`, `git show`.
- There is no deterministic fork router. Every branch decision is a model call,
  so prefer fewer, larger delegations over many small ones.
