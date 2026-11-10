# Starter agent catalog

Apmatia ships five curated, version-controlled prompt profiles in
`src/apmatia/modules/agents/starter_profiles/`: Mira (software engineering),
Luna (Linux administration), Rowan (writing), Belle (general assistance), and
Ivy (creative work). The files use the fields accepted by `AgentPrompt` and
include a stable `profile_id`, a practical specialization, and a distinct
personality. Their prompts explicitly state that persistent memory and Apmatia
tool integrations are disabled. They do not add tools, memory, or generated
agents.

## Built-in starters and custom clones

On a fresh Apmatia setup, the five starters install automatically for the first
user once at least one Apmatia model is configured. They are published through
the existing public-agent API and use the first configured model as their
default, so connected clients such as Ysparr can discover and use them. The
automatic install runs at startup and when the Agents list is opened. It does
not overwrite existing prompts, names, or model choices. Removing the starters
after this one-time install does not cause them to return.

To give a user editable copies of all five starters, sign in as that user and
run the Agents module command `agents.clone_starters`. It can also be called
through the authenticated `POST /api/module-commands/agents.clone_starters`
endpoint:

```json
{
  "payload": {}
}
```

The cloned agents are ordinary private custom agents: their prompts, model
selection, tools, skills, and knowledge configuration are copied from the
starter and can then be changed independently. The operation is idempotent;
running it again does not create another copy for the same user.

## Public starter policy

Built-in starters are public prompt-only agents. They are created without
persistent memory, tools, RAG roots, private knowledge, or other private
metadata. Their prompts also instruct them not to claim persistent memory or
Apmatia tool access.

Apmatia administrators may edit the prompts and model choices of public
starters and may create additional public starter agents. Public status does
not grant access to an administrator's personal capabilities: an agent with a
memory assignment, tool assignment, RAG root, private knowledge root, or
metadata cannot be published. If a public agent is changed to include one of
those capabilities, Apmatia rejects the publication or removes its public
status.

The administrator authorization layer is separate from this capability guard.
When an external identity provider such as Aggregare SSO is connected, its
Apmatia administrator mapping should control who may perform these public
agent changes. Users who need tools or memory should use `agents.clone_starters`
and keep those custom copies private.

## Reapplication and customization

Automatic seeding creates agents and their prompts through `AgentManager`, then
stores the catalog `profile_id` on each built-in agent. Cloning creates a new
prompt and agent record with a `cloned_from_starter_profile_id` management
marker. Cloned agents can be edited or deleted through the normal management
commands.

The catalog files are the starting snapshot for built-in starters. Updating a
catalog file affects future installations only; it is not a migration for
agents already created or cloned.

The `starter_profile_id` is management metadata and is not added to the public
agent contract. A profile's default model can be supplied at installation
time; it is saved as `default_model_id`, while normal Apmatia model selection
and fallback behavior remain in effect.
