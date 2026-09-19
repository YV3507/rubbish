# Security Policy

## Project status

Rubbish is an early-stage, work-in-progress project. It is **not** intended to be
exposed to untrusted networks as-is. Notably, the backend currently ships without
an authentication layer and its `/api/v1/config` endpoint can return configured
secrets. Please run it on a trusted host or behind your own authenticating proxy.

## Supported versions

Only the latest commit on `main` is supported. There are no maintained release
branches yet.

| Version | Supported |
| :--- | :--- |
| `main` (latest) | :white_check_mark: |
| Older commits / tags | :x: |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately using GitHub's
[Report a vulnerability](https://github.com/YV3507/rubbish/security/advisories/new)
form. If that is unavailable, contact the maintainer
[@YV3507](https://github.com/YV3507) directly.

Please include:

- A description of the issue and its impact.
- Steps to reproduce, or a proof-of-concept.
- The affected component (backend / compute-node / frontend) and commit.
- Any suggested mitigation, if you have one.

## What to expect

- Acknowledgement of your report as soon as possible.
- An assessment and, where confirmed, a fix on `main`.
- Credit in the advisory once a fix is published, unless you prefer to stay anonymous.

## Known limitations (not vulnerabilities)

These are documented, accepted limitations of the current prototype rather than
undisclosed security bugs:

- No authentication or authorisation on any HTTP/WebSocket endpoint.
- CORS is configured permissively for local development.
- Tool execution (`shell`, `file edit`) is not sandboxed and is not gated by a
  permission prompt yet.
- The code-graph indexer will read any path the process can access.
