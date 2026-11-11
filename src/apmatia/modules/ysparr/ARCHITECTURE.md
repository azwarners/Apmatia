# Ysparr adapter architecture

Standalone Ysparr owns the relay, durable job store, streaming path, and
model/backend routing. Apmatia owns agent records and contributes a small
versioned extension over HTTP.

The extension exposes a public catalog of published agents and a resolver that
receives a read-only request view. It returns only additive role-aware
contributions and target metadata such as `preferred_model_type`; it never
selects a provider model, edits history, or runs inference.

`YsparrClient` is the Apmatia-side client for model discovery, completion
submission, cancellation, and streaming. It imports no Ysparr implementation
modules.

The extension endpoints are read-only and can require a bearer token through
`APMATIA_YSPARR_EXTENSION_API_KEY`; Ysparr sends the corresponding
`YSPARR_EXTENSION_API_KEY` value.

The optional memory-tool extension is separate from model resolution. It
revalidates the mapped principal and private-agent ownership on every list and
invocation request, then uses Apmatia's existing assigned-tool runtime. Its
provider speaks Sidecaravan's newline-delimited MCP contract and never imports
Memkeeper or accepts a caller-supplied team token.
