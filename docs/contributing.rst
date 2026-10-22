Contributing
================

``tmdl-drift-doctor`` is a Python CLI that detects and remediates drift
across a fleet of TMDL-format Power BI semantic models derived from one
template: you maintain one golden model, and the tool cascades its
truth back out to the per-client copies, safely and auditably.
Contributions of all kinds are welcome: new drift kinds, bug fixes,
docs, and example fleets.

Development setup
---------------------

Requires Python 3.10 or later.

::

    $ git clone <your-fork-url> tmdl-drift-doctor
    $ cd tmdl-drift-doctor
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install -e ".[dev]"
    $ pytest

(On Windows, activate with ``.venv\Scripts\Activate.ps1`` instead.) The
editable install puts the ``drift-doctor`` console command on your
PATH, so code changes are picked up immediately. Try it against the
bundled example fleet, copied somewhere writable first, since running
the tool writes state and edits models:

::

    $ cp -r examples/fleet /tmp/gym-fleet && cd /tmp/gym-fleet
    $ drift-doctor capture
    $ drift-doctor detect

See ``examples/README.md`` in the tool repository for the full guided
walkthrough (capture, detect, remediate, ledger, plus retirement and
revival).

Project layout
------------------

::

    src/tmdl_drift_doctor/
    |-- cli.py             # Click entry point: the 20 commands
    |-- fleet.py           # fleet.yml loader + Fleet (paths, allowlist, gating, overrides)
    |-- overrides.py       # resolve per-model overrides; what each one acknowledges
    |-- tmdl.py            # TMDL parser (tables, measures, relationships, hierarchies)
    |                      #   + string-aware normalization and DAX references
    |-- baseline.py        # `capture`: snapshot the template, maintain retirements
    |-- detect.py          # `detect`: typed Findings, coupling guard, JSON report
    |-- remediate.py       # `remediate`: appliers, preconditions, phases, --converge
    |-- tmdl_edit.py       # guarded raw-block TMDL surgery + write validators
    |-- ledger.py          # append-only JSONL audit trail (retire/revive/remediated)
    |-- ratchet.py         # `ratchet check|tighten`: per-model floors
    |-- audit.py           # `audit`: re-verify applied fixes from the ledger
    |-- review.py          # `review`: the human review checklist
    |-- interactive.py     # the confirmation runner and the batch-safe rules
    |-- annotations.py     # `Category_*` annotations in model.tmdl
    |-- applied_filters.py # the `i-Applied Filters` measure and its coverage
    |-- blast.py           # `diff`: the blast radius of a change
    |-- cascade.py         # the cascade summary: is each model a clean superset?
    |-- category_filters.py # the `f-` category gates
    |-- enrichment.py      # view-enrichment notices and their registry
    |-- families.py        # named sets of fleet models
    |-- fieldparams.py     # field-parameter tables: a lossless row reader/writer
    |-- freshness.py       # `freshness`: a branch that predates the main line
    |-- groups.py          # analysis groups: the graph, the plan, the layered drop
    |-- hygiene.py         # override hygiene: a declaration that protects nothing
    |-- mapping_codec.py   # the encoded "Enter data" string codec
    |-- mappings.py        # encoded mapping tables in the drift pipeline
    |-- markers.py         # client extension markers in derived-only text
    |-- measure_ops.py     # named measure removals outside the retirement channel
    |-- metrics.py         # template metrics and the count floors
    |-- named.py           # `remediate --ref`: push named measures to every model
    |-- purge.py           # the pristine-category purge (`purge.*`, sync mode)
    |-- receipt.py         # the sync receipt (`<state_dir>/last_sync.json`)
    |-- refresh.py         # incremental-refresh parity for fact tables
    |-- renames.py         # measure and column renames; the rename map
    |-- roles.py           # table roles and measure classes: the one definition
    |-- selectors.py       # selector measures: SWITCH arms
    |-- sensors.py         # removing a dead table sensor from a DAX expression
    |-- sources.py         # source identity: which view a partition reads
    |-- visibility.py      # the visibility rules

    tests/              # pytest suite + tests/fixtures/fleet/ (the seeded fleet)
    examples/fleet/     # runnable gym-chain fleet with drift pre-seeded

The full documentation (a tutorial, how-to guides, and reference) lives
in this separate ``tmdl-drift-doctor-documentation`` repository,
published on Read the Docs.

The mental model
---------------------

Three commands form the core pipeline, and every design decision
follows from it:

1. ``capture`` snapshots the template into a committed baseline and
   maintains the retirement record; anything dropped from the template
   since the last capture becomes a ``retired`` ledger event.
2. ``detect`` compares each derived model, parsed live from disk,
   against the baseline plus the retirement record and emits typed
   ``Finding`` objects. It is read-only and CI-friendly, exiting 1 when
   remediable drift exists.
3. ``remediate`` consumes those findings and applies a per-kind fix,
   cascading template truth into the derived models.

Around them sit seventeen more commands, all documented in the
CLI and configuration reference: ``ratchet check|tighten`` (the CI
gate), ``audit`` (did the applied fixes stay applied), ``review`` (the
human queue), ``ledger`` (the record, and a manual revival), and the
surrounding work of the fleet: ``diff``, ``freshness``, ``groups``,
``mapping``, ``overrides``, ``purge``, ``rename``, ``renames``,
``retire``, ``add-branch``, ``fieldparam``, ``fleet`` and
``enrichment``.

Safety gates: do not weaken these without discussion
----------------------------------------------------------

- **Allowlist.** Nothing cascades by default. A drift kind the fleet's
  ``allowlist.kinds`` does not name is detected and reported, never
  applied. Shared expressions are compared only if individually named
  under ``allowlist.expressions``, so a careless cascade can never
  repoint a per-tenant connection parameter.
- **``--sync``, double-gated deletions.** The only removals ever
  proposed are of objects provably retired from the template
  (``retire.*`` kinds) and of the pristine-category purge items, and
  applying them requires both the allowlist entry and the ``--sync``
  flag. A default ``remediate`` run is purely additive or overwriting.
- **A question before every write.** ``remediate`` confirms each fix
  with the operator on a terminal. Without a terminal the questions are
  disabled, every item is treated as a "no", and the run writes
  nothing.
- **``--yes`` is batch-safe, and only with a ``--kind``.** ``--yes``
  applies without asking, but only the kinds in
  ``remediate.BATCH_SAFE_KINDS``, and only when the command line names
  at least one ``--kind``: ``--yes`` on its own is a usage error, so a
  scripted run can never apply every allowlisted kind by accident.
- **``--sync --confirm-deletions``.** A deletion is never applied under
  ``--yes``, in a batch run, or without a terminal. In a scheduled job
  it needs the explicit second confirmation, which is a separate flag
  from ``--sync`` on purpose: the two decisions are "may this run
  delete" and "do I mean it".
- **Ledger.** Every retirement, revival, and applied fix is one
  immutable, append-only JSONL line. A retirement recorded at
  recapture is the only thing that ever authorizes a downstream
  deletion; a revival cancels a retirement without erasing history, so
  a deliberate re-add is never re-removed.
- **Baseline-recapture discipline.** ``detect`` and ``remediate``
  refuse to run on a stale baseline, since a stale baseline
  misclassifies drift: a retired object looks missing and gets
  resurrected. The refusal is a configuration error, so it exits 2 and
  never 1. ``--allow-stale`` overrides, at the caller's own risk.
  Recapture the moment the template changes.
- **OVERLAY protection.** A file a model has and the template does not
  is hashed before the run writes anything. An ordinary fix that would
  write one fails with an ``OVERLAY`` error, and a change to one that
  no fix declared fails the run. A model's own work is never
  collateral damage.
- **``--backup``.** One ``<file>.bak_<timestamp>`` copy per file
  before its first write in a run; the copies are removed when the run
  succeeds and kept when anything failed. Git stays the recommended
  undo.
- **Guarded TMDL surgery.** Edits splice raw text blocks, never
  re-serialize from parsed fields, so annotations and formatting
  survive. Lineage tags are regenerated on insert and preserved on
  overwrite, and every new file content passes
  ``tmdl_edit.assert_tmdl_valid`` before it touches disk, including the
  invariant that a property line is never injected into a DAX
  expression body, which broke every affected measure fleet-wide the
  one time it happened for real. See "Design: safe TMDL surgery" in
  the CLI and configuration reference.

Adding a new drift kind
---------------------------

Drift kinds are named ``family.detail`` (for example
``measure.expression_drift``), and that string is what users put in
their allowlist, so choose it with care. Work through these files in
order:

1. **``detect.py``.** Emit a ``Finding(kind="your.kind", ...)`` in
   ``detect_model`` where the divergence is discovered. Register the
   kind in the right tuple at the top of the module:
   ``REMEDIABLE_KINDS`` (has an automated fix), ``ADVISORY_KINDS``
   (report-only, never applied), ``SYNC_ONLY_KINDS`` (offered only in a
   ``--sync`` run), and, or, ``RETIREMENT_FINDING_KINDS`` (a deletion,
   automatically ``--sync``-gated). ``ALWAYS_GATING`` holds the kinds
   that fail a gate whatever the allowlist says. Stash any
   surgery-time extras on ``Finding.data``.
2. **``tmdl_edit.py``.** If the fix needs a new text operation, add a
   guarded raw-block helper there. Splice raw blocks; never rebuild
   TMDL from parsed dataclasses. Confirm ``assert_tmdl_valid`` still
   accepts the output.
3. **``remediate.py``.** Write an applier, ``_apply_your_kind(fleet, f)``,
   that returns ``(label, [FileChange])`` (a ``FileChange`` with
   ``old=None`` creates, ``new=None`` deletes) and register it in the
   ``APPLIERS`` dict. The engine handles overrides, the allowlist,
   ``--sync``, blocked retirements, dry-run, and pre-write validation;
   appliers must be idempotent, so a second run finds nothing to do. If
   the fix relies on something else existing, add a precondition to
   ``PRECONDITIONS`` and place the kind in ``PHASES``; if an override
   should be able to acknowledge it, add it to ``overrides.SUPPRESSES``.
   A kind a ``--yes`` run may apply without a person belongs in
   ``BATCH_SAFE_KINDS``; a kind that deletes something belongs in
   ``DESTRUCTIVE_PREFIXES``.
4. **Fixtures and tests.** Seed the new drift in
   ``tests/fixtures/fleet/`` (the fixture fleet doubles as the suite's
   readable specification) and add coverage under ``tests/`` (detection,
   allowlist gating, remediation, idempotence; safety-critical surgery
   goes in ``tests/test_tmdl_edit_safety.py``).
5. **Docs.** Document the kind in the drift-kind catalog reference in
   this documentation set, add it to the drift-kinds table in the tool
   repository's ``README.md``, and note any new safety consideration
   under "Do not cascade blindly when" if it introduces one.

Before you open a PR
-------------------------

Run the suite and confirm it is green:

::

    $ pytest

For changes that touch detection, remediation, or TMDL surgery, also
exercise the CLI end to end against a fresh copy of the example fleet
(``capture``, ``detect``, ``remediate --dry-run``, ``remediate``, a
second ``remediate`` for idempotence, ``ledger``) and confirm the
output matches expectations. Exercise the non-interactive path too: a
``remediate`` with no terminal must apply nothing, and a
``remediate --yes --kind ...`` must apply only the batch-safe kinds.
New behavior needs new tests.

Commit and PR conventions
------------------------------

- Write focused commits with imperative, present-tense subjects (for
  example "Add hierarchy.missing drift kind," not "Added..."). Keep
  unrelated changes in separate commits.
- Reference the issue being addressed in the commit body or PR
  description.
- Open one PR per logical change. Explain what changed and why, and
  note any impact on the safety gates or the ledger and baseline
  formats. Confirm ``pytest`` passes and describe how the change was
  exercised.
- Docs-only or example-only changes are welcome and should say so.

Issues
---------

When filing a bug, include: the ``drift-doctor`` version, your Python
version and OS, the command you ran, and the full output (findings,
diffs, or the error). A minimal ``fleet.yml`` and the smallest TMDL
snippet that reproduces the problem help enormously; the fixture fleet
under ``tests/fixtures/fleet/`` is a good template for a reproduction.
For feature requests, describe the drift that needs catching or
cascading and why the existing kinds do not cover it.

Report security-sensitive issues, for example a way to make the tool
write malformed or unintended TMDL past the guards, privately to the
maintainer rather than in a public issue.

License
-----------

By contributing, you agree that your contributions are licensed under
the project's MIT License, the same as for the rest of the project.
