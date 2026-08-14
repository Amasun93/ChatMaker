# Evidence Status Model

ChatMaker records evidence at the smallest honest boundary. A later gate never inherits success from an earlier gate.

## Pack gates

- `source_reviewed`: A human or agent checked the record's technical claims against its cited source.
- `code_compiled`: The exact example source compiled for the exact board identity.
- `firmware_uploaded`: The resulting firmware uploaded to one identified wired board.
- `physical_effect_verified`: The expected real-world effect was observed and recorded.

Each gate is one of:

- `unverified`: No sufficient evidence has been collected.
- `verified`: Dated evidence is recorded.
- `failed`: A check was run and failed; the evidence describes the failure.
- `not_applicable`: The gate cannot apply to this record.

Initial records deliberately use `unverified`. Adding an official URL is not the same as reviewing the source, and creating an example is not the same as compiling or uploading it.

## Runtime stages

Runtime reports may add environment discovery, serial evidence, page rendering, and browser interaction. These help diagnose a project but do not replace the four pack gates.

Serial reports keep `serial_evidence`, observed lines, expected-marker match, malformed-text warnings, and restart-loop suspicion separate from upload and physical effect. A timeout or empty read remains an explicit unverified result.
