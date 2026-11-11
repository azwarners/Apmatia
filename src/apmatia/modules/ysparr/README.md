## Ysparr adapter

The Apmatia Ysparr module is an adapter to the standalone Ysparr service. It
does not execute models, own model backends, or persist Ysparr jobs locally.

`apmatia.modules.ysparr.client.YsparrClient` provides the small external HTTP
client used by Apmatia-owned callers. The module also publishes the versioned
read-only extension at `/api/public/ysparr/catalog` and
`/api/public/ysparr/resolve`.

Agent entries contain stable selectors and non-secret target metadata.
Unauthenticated or unmapped callers receive only published public names;
mapped callers additionally receive their own eligible private agents.
Resolution receives a read-only request view and returns additive
system/developer-role contributions; it cannot alter messages, history, model
selection, or earlier contributions.

For deployments where the Apmatia API is not otherwise protected, set
`APMATIA_YSPARR_EXTENSION_API_KEY` on Apmatia and the matching
`YSPARR_EXTENSION_API_KEY` on Ysparr. Leave it unset only when the service
boundary is already protected by the deployment network.

For authenticated Ysparr callers, the adapter accepts the stable Ysparr
principal ID only when it is accompanied by an HMAC-SHA256 proof made from the
shared extension key. Configure an explicit JSON mapping from Ysparr principal
IDs to existing Apmatia user IDs in `APMATIA_YSPARR_PRINCIPAL_MAP`. A mapped
principal receives its own eligible private agents plus public starters;
unmapped or missing principals receive public starters only, and private
selectors fail closed.

When Sidecaravan is enabled (`APMATIA_SIDECARAVAN_ENABLED=1` and either
`SCV_TOKEN` or a readable `SCV_TOKEN_FILE`),
the authenticated extension also exposes the selected private agent's assigned
memory tools:

* `GET /api/public/ysparr/agents/{agent_id}/tools` returns assigned
  `memory.recall` and `memory.save` definitions.
* `POST /api/public/ysparr/agents/{agent_id}/tools/{tool_name}` accepts
  `{"arguments": {...}, "call_id": "...", "approval_granted": false}` and
  returns the normal Apmatia tool result.

Both endpoints require the extension bearer key and a valid HMAC principal
assertion. The mapped principal must own the private agent; this check runs on
every request. Sidecaravan is called only through its `scv-mcp` MCP boundary,
and retrieved content includes source metadata and remains untrusted data.
