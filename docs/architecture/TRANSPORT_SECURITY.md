# Transport Security

Apmatia now enforces transport security centrally so it does not silently expose sensitive traffic over plaintext on a LAN or public network.

## Policy Overview

The canonical server config lives under `server.transport_security`.

```yaml
server:
  host: 127.0.0.1
  port: 8000
  transport_security:
    policy: development
    tls:
      enabled: false
      cert_file: null
      key_file: null
      ca_file: null
    allow_insecure_non_loopback: false
```

### `development`

Plain HTTP is allowed only when Apmatia is bound to loopback.

Use this when traffic never leaves the local machine:

```yaml
server:
  host: 127.0.0.1
  transport_security:
    policy: development
    tls:
      enabled: false
    allow_insecure_non_loopback: false
```

TLS is still allowed on loopback if you want to test HTTPS locally.

The explicit override `allow_insecure_non_loopback: true` exists only for deliberate temporary diagnostics. It exposes Apmatia traffic in plaintext and emits a startup warning.

### `lan`

TLS is required.

```yaml
server:
  host: 0.0.0.0
  transport_security:
    policy: lan
    tls:
      enabled: true
      cert_file: /path/to/apmatia.crt
      key_file: /path/to/apmatia.key
    allow_insecure_non_loopback: false
```

Use a certificate whose subject or SANs match the hostnames and IPs clients will use. For a private CA or self-signed certificate, each client must trust that CA or certificate explicitly.

### `internet`

TLS is required and plaintext is rejected everywhere.

Use this only when Apmatia is intentionally reachable beyond a private LAN. The current implementation validates certificate usability locally and rejects missing, unreadable, malformed, mismatched, or expired certificate material when it can be checked at startup.

## Reverse Proxy Deployment

A safe reverse-proxy setup keeps Apmatia itself on loopback and terminates TLS at the proxy:

```text
Client
  |
  | HTTPS
  v
Caddy / nginx / Traefik
  |
  | HTTP over loopback only
  v
Apmatia bound to 127.0.0.1
```

This is the preferred way to front Apmatia with a proxy. Do not use a proxy as justification for binding Apmatia itself to plaintext on `0.0.0.0`.

## Docker Loopback Publication

Docker development is a separate deployment boundary from a normal LAN bind.

In this mode, Apmatia may bind to all interfaces inside the container while Docker publishes the port only on host loopback.

```text
Process bind address inside container: 0.0.0.0
Host-side Docker publication address: 127.0.0.1
```

The operator must explicitly assert this boundary with:

```yaml
server:
  transport_security:
    container_host_loopback_only: true
```

This is not the same as `allow_insecure_non_loopback`. The container-loopback flag does not mean "ignore transport security"; it means "the process is inside a container whose published port is restricted to localhost on the host".

Example Docker Compose publication:

```yaml
ports:
  - "127.0.0.1:8000:8000"
  - "127.0.0.1:8501:8501"
```

## Dangerous Override

`allow_insecure_non_loopback: true` is a narrow, temporary escape hatch for local debugging.

It:

- exposes Apmatia traffic in plaintext;
- must never be used for normal LAN or Internet deployments;
- produces a startup warning;
- may later be surfaced by the Apmatia Hardening module as a critical finding.
