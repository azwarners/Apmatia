# Starter agent catalog

Apmatia ships five curated, version-controlled prompt profiles in
`src/apmatia/modules/agents/starter_profiles/`: Mira (software engineering),
Luna (Linux administration), Rowan (writing), Belle (general assistance), and
Ivy (creative work). The files use the fields accepted by `AgentPrompt` and
include a stable `profile_id`, a practical specialization, and a distinct
personality. Their prompts explicitly state that persistent memory and Apmatia
tool integrations are disabled. They do not add tools, memory, or generated
agents.

## Install

On a fresh Apmatia setup, the five starters install automatically for the first
user once at least one Apmatia model is configured. They are published through
the existing public-agent API and use the first configured model as their
default, so connected clients such as Ysparr can discover and use them. The
automatic install runs at startup and when the Agents list is opened. It does
not overwrite existing prompts, names, or model choices. Removing the starters
after this one-time install does not cause them to return.

To install the catalog manually, sign in as the user who should own the profiles,
then run the existing Agents module command `agents.install_starters`. It can
also be called through the authenticated
`POST /api/module-commands/agents.install_starters` endpoint:

```json
{
  "payload": {
    "default_model_id": 12,
    "publish": false
  }
}
```

Both options are optional. Omit `default_model_id` to leave model selection
unconfigured, or pass an Apmatia model-config ID to set that default on newly
installed agents. No particular LLM backend is assumed. `publish` defaults to
`false`; the automatic install publishes the profiles. The public-agent API
continues to return only its stable public shape: agent ID, name, compiled
system prompt, and optional non-secret model mapping.

## Reapplication and customization

Installation creates agents and their prompts through `AgentManager`, then
stores the catalog `profile_id` on each agent. Reapplying the command adds
missing profiles and reports existing profiles as `already_installed`. It
never resets an installed profile's name, prompt, model selection, or
publication state. A name already used by a non-catalog agent is reported as a
`name_conflict` and left untouched. Installed agents are ordinary Apmatia
agents and can be edited or deleted through existing management commands.

The catalog files are the starting snapshot for new installations. Updating a
catalog file affects future installations only; it is not a migration for
agents already installed. Manual reapplication with `publish: true` does not
publish previously installed profiles. To change publication later, use the
existing authenticated agent update API and its publication eligibility checks.

The `starter_profile_id` is management metadata and is not added to the public
agent contract. A profile's default model can be supplied at installation
time; it is saved as `default_model_id`, while normal Apmatia model selection
and fallback behavior remain in effect.
