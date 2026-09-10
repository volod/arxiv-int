# Archive Organization

Archive organization physically places files into a classified directory tree. It is a separate
maintenance utility, never an ordinary pipeline stage: it consumes one accepted, complete
classification artifact and produces a deterministic plan for exactly one declared silo.

**Availability: planned.** `arxiv-int archive reorganize` is not registered yet; `arxiv-int archive
--help` currently lists only `locate` and `import-ledger`. The behavior below is the reviewed target
defined by the [specification](../design/spec.md#separate-archive-organization-utility) and
tracked in the [forward plan](../impl/plan.md#separate-archive-organization----archive-organization).
Use this page to plan an organization session, not to run one today.

## Why it stays separate

Analysis never moves the operator's files. The normal pipeline and every container mount the archive
read-only, and full-corpus authorization never depends on applying a placement. `archive-organization`
owns physical placement; `archive-classification` owns only the classification map. The organizer
works from a sealed classification export and source manifest, without model inference,
reclassification, or live search and graph services.

## End-to-end command

Preview first. Dry-run is the default and the only mode that needs no separate authorization.
Replace `CLASSIFICATION_PATH` and `SILO_ID` with reviewed values, and `TARGET_DIR` with a root that
does not overlap the silo, results or database roots.

```bash
arxiv-int archive reorganize --classification CLASSIFICATION_PATH --silo SILO_ID \
  --mode copy --target TARGET_DIR
```

The plan lists hierarchical directory and file names, unresolved cases, collisions and capacity
checks. Source files stay intact. Applying a reviewed plan is a second, explicit step:

```bash
arxiv-int archive reorganize --apply --plan PLAN_PATH
```

`--resume PLAN_ID` and `--rollback PLAN_ID` continue or reverse only operations the sealed ledger
proves. After a placement, `arxiv-int archive import-ledger PATH` imports the portable path-event
ledger so `arxiv-int archive locate DOCUMENT_ID` and later pipeline updates keep finding sources.

## Placement modes

The mode is part of the authorized decision.

| Mode | Effect | Cost and risk |
| --- | --- | --- |
| `copy` to `--target DIR` | Builds the classified tree in a separate target root and leaves the silo untouched. | Needs free space for the selected subset. The source archive is never modified, so the target can be deleted and rebuilt at any time, on the same or a different device. |
| `move` in place | Renames files inside the silo root into their class directories. | Reclaims no extra space but rewrites the operator's own tree. Requires a writable archive and a verified backup, and stays same-filesystem. |

`copy` is the default and the recommended first organization: it turns an accepted classification
into a browsable subject tree without putting originals at risk. Hardlinks are excluded, because
later target edits would also alter the source. Both modes read the same classification mapping,
write the same ledger, and support the same resume, verification and lookup behavior.

## Safety boundaries

- Every apply revalidates source paths, available content hashes, destinations, free-space and
  device conditions, and the classification fingerprint.
- Entries lacking the permissions or strong hash needed for a safe placement stay explicitly blocked.
- The command never overwrites a destination, never follows a link outside the selected root, and
  never relocates a virtual archive member independently of its container.
- Stale, colliding, overlong or incompletely accounted plans are refused. A `move` plan additionally
  refuses cross-device entries; a `copy` plan refuses a target overlapping the silo, results or
  database root.
- A plan excludes concurrent pipeline scans and other placement writers for its silo.
- Original provenance is never rewritten to contain only the new path. In `copy` mode the original
  location remains the source of record and the target path is recorded as an additional location.
- Atomic per-file renames do not make a multi-file move atomic; durability comes from flushing the
  journal and directory metadata around each operation.

## Directory and name policy

Physical directories follow the primary class's ancestor path. Each segment combines a reversible
safe class token with a short meaningful ASCII slug, is capped at a configured byte length, and is
checked with the full destination against filesystem component and path limits. Dedicated ASCII
directories such as `_unclassified` and `_unreadable` hold exceptional outcomes that can still be
placed safely. Complex facets and secondary classes stay in metadata. Filenames are preserved where
safe, with deterministic content or occurrence suffixes for duplicate basenames and normalized-name
collisions. Directory slugs never derive from unvalidated model text.

## Before a real placement

No real archive placement is accepted without review of the mapping, thresholds, directory
vocabulary, dry-run diff and target space, and, for `move`, backup and recovery readiness.
Placement fixtures prove byte-identical contents in both modes, one-to-one path accounting,
collision refusal, interruption and resume, rollback, and source lookup.
