# Hardware Verification Gates

Report each gate separately:

1. `source_reviewed`: The board/component facts were checked against the cited source.
2. `code_compiled`: The exact generated source compiled for the exact board identity.
3. `firmware_uploaded`: The upload command exited successfully for one identified wired device.
4. `physical_effect_verified`: The expected real-world behavior was observed and recorded.

Serial evidence is useful diagnostic evidence but does not replace physical confirmation. An upload exit code does not prove the sketch survived restart. Record failures and unverified gates without upgrading them.

