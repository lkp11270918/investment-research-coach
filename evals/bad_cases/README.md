# Bad Case Registry

Every real or synthetic failure is stored as an immutable JSON case with:

- `case_id`, `requirement_id`, `discovered_at`, and `source`;
- sanitized input or a licensed source reference;
- expected behaviour from an independent annotator;
- actual behaviour, model/version, and failure taxonomy;
- regression test path and resolution commit when fixed.

Cases are never deleted to improve a score. Sensitive user content must be
redacted or referenced by a non-public identifier.
