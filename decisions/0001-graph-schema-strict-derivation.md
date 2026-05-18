# Strict reject of unknown columns at load time

Files loaded or appended into a koza graph database have their columns validated against the union of (Biolink slots ∪ koza extras ∪ every operation's declared outputs). Columns matching nothing in that union cause the load to fail with a clear error rather than being carried through.

We rejected "carry unknown columns through opaquely" because it lets schema drift hide in the data and breaks the property that operations can trust the schema. We rejected "quarantine to a side table" because the same drift risk applies — downstream operations still can't trust the active schema. We rejected "user-authors a full LinkML schema" because we want to defer formal authoring until a driving use case appears (per-flag overrides like `--single-valued-category` stay in koza for now).

The strict-reject set is computed by the schema module at import time: Biolink comes from the stored copy inside the graph database (see ADR-0002), koza extras and operation-declared outputs come from a hardcoded import list of operation modules. Append re-uses the same set, so new Biolink-recognized slots and new operation-declared outputs are admitted without manual intervention.
