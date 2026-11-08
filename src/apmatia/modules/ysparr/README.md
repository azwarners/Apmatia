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
