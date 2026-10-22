CLI and configuration reference
================================

Every command, flag and exit code of ``drift-doctor`` 1.2.1, the
``fleet.yml`` schema, the state files, and the design decisions behind
``remediate`` that a reader needs before trusting it against a real
fleet. Flags are copied from each command's ``--help``; outputs come
from runs on the example fleet in the tool repository.

Commands
-----------

``drift-doctor`` has twenty commands. Every command that reads a fleet
takes ``--fleet PATH`` (default ``fleet.yml``); ``mapping decode|diff|union``
and ``fieldparam retag`` work on files you name and take no
``--fleet``, and ``diff`` takes it only to check the baseline.

.. list-table::
   :header-rows: 1

   * - Command
     - What it does
   * - ``capture``
     - Snapshot the template into the baseline; record retirements and
       revivals in the ledger.
   * - ``detect``
     - Detect drift in every derived model. Read-only.
   * - ``remediate``
     - Cascade template truth into the derived models (allowlist-gated).
   * - ``ratchet check`` / ``ratchet tighten``
     - Fail CI when drift rises above the recorded per-model floors;
       lower the floors.
   * - ``audit``
     - Re-verify every applied fix in the ledger.
   * - ``review``
     - Write a per-model checklist of everything routed to a person.
   * - ``ledger``
     - Show the ledger, or record a manual revival.
   * - ``diff``
     - Compare two detection reports and write what the change reaches.
   * - ``freshness``
     - Warn that a branch predates retirements the main line has made.
   * - ``add-branch``
     - Clone each SWITCH arm of a sibling measure for a new one.
   * - ``enrichment report`` / ``enrichment rescan``
     - Render, and re-check, the view-enrichment register.
   * - ``fieldparam retag``
     - Move field-parameter rows from one category to another.
   * - ``fleet check`` / ``fleet connection`` / ``fleet family``
     - Validate the configuration and answer questions about its models.
   * - ``groups plan`` / ``groups annotate`` / ``groups drop`` / ``groups drop-table``
     - Plan and drop analysis groups (subject areas) safely.
   * - ``mapping decode`` / ``mapping diff`` / ``mapping union``
     - Read and merge encoded entered-data mapping tables.
   * - ``overrides check`` / ``overrides files`` / ``overrides is-exempt``
     - Inspect the declared divergence in ``fleet.yml``.
   * - ``purge``
     - Remove named measures from the chosen models.
   * - ``rename measure``
     - Rename a measure everywhere it is used.
   * - ``renames check`` / ``renames apply``
     - The reviewed rename map (``renames:`` in ``fleet.yml``).
   * - ``retire``
     - Retire a superseded measure in the template and every model.

.. list-table:: Exit codes
   :header-rows: 1

   * - Code
     - Meaning
   * - 0
     - Success: clean, nothing actionable, floors held, no reverts,
       nothing to do.
   * - 1
     - The command's own "not clean" answer: actionable drift
       (``detect``), a rise, a missing floor or a resurrection
       (``ratchet check``), a failed fix (``remediate``), a revival with
       no retirement in force (``ledger --revive``), a stale declaration
       (``overrides check``), a rename target that does not exist
       (``renames check``), no model declaring the old name
       (``rename measure``), a stamping table that disagrees
       (``fleet check --stamps``), or an empty family (``fleet family``).
   * - 2
     - A usage or configuration error: an unknown option, a malformed or
       unresolvable ``fleet.yml``, an unknown ``--model``, a stale
       baseline, ``--yes`` without ``--kind``, ``--confirm-deletions``
       without ``--sync``, an unknown ``remediate --ref`` name, a report
       ``ratchet`` or ``diff`` cannot trust or read, a floors file it
       refuses, a precision loss in ``rename measure`` without
       ``--format-arm``. **A stale baseline is a configuration problem,
       not a finding**, so a CI job reads it as "the run could not be
       done" and never as "the model has drift".
   * - 3
     - A derived model could not be parsed (``detect``, ``audit``), or a
       path is not exempt (``overrides is-exempt``).
   * - 4
     - ``audit`` found a reverted fix.
   * - 5
     - ``enrichment rescan`` printed advisory warnings: a registry entry
       records columns the model no longer has.
   * - 130
     - The run was interrupted with Ctrl-C. The edits already accepted
       are written and valid; re-run to resume from the remaining items.

``drift-doctor capture``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Snapshot the template into ``<state_dir>/baseline.json`` and maintain
the retirement record. Run it the moment the template changes.

::

    $ drift-doctor capture
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=17 measures=9 relationships=3 mapping_rows=4 expressions=3

It parses the live template and writes the snapshot as the baseline
(snapshot format **3**: tables, columns, measures, shared expressions,
mapping rows and relationships, plus ``metrics``, ``fact_tables``,
``table_source_views``, ``captured_at`` and ``provenance``). If a
previous baseline exists, it compares the two: an object present before
and absent now becomes a ``retired`` ledger event, printed as it is
recorded, and a retired object present again becomes a ``revived``
event.

::

    $ drift-doctor capture
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=16 measures=8 relationships=3 mapping_rows=4 expressions=3
      [ledger] retired column: Classes[Capacity]
      [ledger] retired measure: Classes[Class Fill Rate %]

The retirement kinds are ``table``, ``column``, ``measure``,
``mapping_row``, ``mapping_category`` and ``relationship``. A column or
measure of a dropped table is covered by the table's event, which lists
the table's objects in an ``objects`` field. Relationships are always
recorded, even when an endpoint table was dropped, because that event
is what later lets ``retire.table`` remove the relationship from a
derived model. A template table re-pointed to another source view is
recorded once, as a ``source_view_change`` event.

``detect`` and ``remediate`` refuse a baseline written in another
snapshot format, with exit 2. A baseline written by 1.1.0 is format 2:

::

    $ drift-doctor detect
    Error: the committed baseline uses snapshot format 2, and this drift-doctor writes format 3 (it now compares shared expressions with their comments and records template metrics). Run `drift-doctor capture` once to upgrade it; the ledger is kept as is.

``drift-doctor detect``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read-only drift detection for every derived model.

::

    drift-doctor detect [--json] [--model NAME] [--kind PREFIX] [--csv] [--sync] [--allow-stale]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--json``
     - Print the schema version 2 report (below) instead of text.
   * - ``--model NAME``
     - Only the named derived model. An unknown name exits 2.
   * - ``--kind PREFIX``
     - Only findings whose kind starts with the prefix. The prefix
       matches at a segment boundary: ``measure`` covers every
       ``measure.*`` kind, ``retire`` and ``retire.`` both cover the
       retirement kinds, and ``measure.miss`` covers nothing. A
       filtered run prints no cascade report.
   * - ``--csv``
     - One CSV row per model, with the shape and the drift by bucket.
   * - ``--sync``
     - Also report the sync-only channel (the pristine-category purge
       items).
   * - ``--allow-stale``
     - Proceed even if the template changed since the last capture, at
       the risk of misclassified findings.

A finding is **actionable** when its kind is in ``allowlist.kinds`` or
is one of the two kinds that always gate (``model.count_below_template``
and ``retire.stranded_ref``), it is not advisory, and no override
acknowledges it. ``detect`` exits 1 when any actionable finding sits on
a model whose ``gating`` is not ``advisory``, 3 when a model could not
be parsed (the other models are still reported), and 2 on a
configuration problem or a stale baseline.

The text report tags each finding: ``[advisory]`` (the model's own
work, never removed without a person), ``[not allowlisted]`` (its kind
is not in ``allowlist.kinds``) and ``[blocked]`` (a retirement that the
model's own work depends on, with a ``blocked:`` line per reason). An
advisory model's header says ``(gating: advisory)``. Findings an
override acknowledges print as an ACK block:

::

      declared divergence honored (overrides): 1 item(s)
      ACK measure.expression_drift   Visits[Total Visits]  [expression; owner charlie-analytics, added 2026-10-22]
          reason: charlie excludes zero-minute visits by contract

A closing line counts ``actionable``, ``advisory``, ``overridden`` and
``errors``. An unfiltered run ends with the cascade report: one block
per model, ``[OK  ]`` when the model has everything the template has,
``[GAP ]`` with what it is missing, ``[FAIL ]`` when it could not be
checked, each with the model's shape (``fact_tables``, ``f_measures``,
``user_facing``, ``helpers``), then ``Summary: <passing>/<total> models
in cascade`` and, when a model failed, ``(N not checked)``:

::

    [GAP ] alpha
        fact_tables=4 f_measures=0 user_facing=9 helpers=1
        - missing: New Members #, Visits per Member
    [FAIL ] bravo
        detection failed — this model was not checked
    Summary: 0/2 models in cascade (1 not checked)

``--csv`` prints the shape and drift buckets instead:

::

    $ drift-doctor detect --csv
    model,tables,measures,fact_tables,filter_measures,user_facing,helpers,gaps,flagged,allowed,expr_drift,col_drift,rel_drift
    alpha,5,10,4,0,9,1,2,2,0,1,0,0
    bravo,4,8,3,0,7,1,1,1,0,0,2,2

JSON report (schema version 2)
""""""""""""""""""""""""""""""""""

``detect --json`` prints one object. This one comes from a git-tracked
copy of the example fleet, trimmed to one model and two findings:

::

    {
      "schema_version": 2,
      "generated_at": "2026-10-22T16:30:50+00:00",
      "template_tree": "b8a1cae22ff162bd83b11e9dc65e97736a17b249",
      "scope": {
        "fleet": true,
        "models": null,
        "alternate_model": null,
        "targets": ["alpha", "bravo"],
        "kind_filter": null,
        "overrides": null
      },
      "errors": [],
      "models": {
        "bravo": {
          "source_divergent_tables": {},
          "gating": "enforced",
          "decisions": [],
          "findings": [
            {
              "kind": "table.missing",
              "model": "bravo",
              "ref": "Classes",
              "template_value": null,
              "derived_value": null,
              "detail": "...",
              "advisory": false,
              "remediable": true,
              "actionable": true
            },
            {
              "kind": "model.count_below_template",
              "model": "bravo",
              "ref": "measures",
              "template_value": "9",
              "derived_value": "8",
              "detail": "'bravo' has 8 measures, below the template floor of 9",
              "advisory": false,
              "remediable": false,
              "data": {"metric": "measures", "client": 8, "template": 9, "adjustment": 0, "floor": 9},
              "actionable": true
            }
          ],
          "overridden": [],
          "counts": {
            "actionable": 8,
            "advisory": 1,
            "overridden": 0,
            "not_allowlisted": 2,
            "by_kind": {
              "column.missing": 1,
              "column.property_drift": 1,
              "mapping_row.missing": 1,
              "model.count_below_template": 2,
              "relationship.missing": 1,
              "relationship.modified": 1,
              "table.missing": 1
            }
          }
        }
      }
    }

.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``schema_version``
     - Always ``2`` for this format.
   * - ``generated_at``
     - UTC ISO-8601 time of the run.
   * - ``template_tree``
     - The git tree hash of the template directory at ``HEAD``, or
       ``null`` when the template is not in a git work tree.
   * - ``scope.fleet``
     - ``true`` when every model was detected (no ``--model``).
   * - ``scope.models``
     - The models the report covers, or ``null`` on a fleet run.
   * - ``scope.alternate_model``
     - The entry's primary model, when the run was against one of that
       entry's secondary models, or ``null``.
   * - ``scope.targets``
     - Every model the run looked at, whatever the filters.
   * - ``scope.kind_filter``
     - The ``--kind`` prefix, or ``null``.
   * - ``scope.overrides``
     - Always ``null`` in 1.2.1 (the overrides come from
       ``fleet.yml``). ``ratchet tighten`` refuses a report where it is
       set.
   * - ``errors``
     - ``{"model", "error"}`` for every model that could not be parsed.
       A non-empty list means every count is understated.
   * - ``models.<name>.source_divergent_tables``
     - The tables of this model that read another source view than the
       template's.
   * - ``models.<name>.gating``
     - ``enforced`` or ``advisory``.
   * - ``models.<name>.decisions``
     - The items the run routed to a person. They never fail a gate.
   * - ``models.<name>.findings``
     - Every finding not acknowledged by an override, with ``kind``,
       ``model``, ``ref``, ``template_value``, ``derived_value``,
       ``detail``, ``advisory``, ``remediable`` and ``actionable``;
       ``data`` (kind-specific extras) and ``blocked`` (a list of
       reasons) when present.
   * - ``models.<name>.overridden``
     - The acknowledged findings, each with an ``override`` object
       (``object``, ``kind``, ``reason``, ``owner``, ``added``).
   * - ``models.<name>.counts``
     - ``actionable``, ``advisory``, ``overridden``,
       ``not_allowlisted``, and ``by_kind`` (actionable findings per
       kind). The counters can overlap: a kind that always gates counts
       as actionable even when the allowlist does not name it, and then
       also counts as not allowlisted, as bravo's two count floors do
       above.

The report is pure ASCII. Save it as UTF-8 or ASCII without a
byte-order mark; ``ratchet --from-json`` and ``diff`` refuse a file
that starts with one (see :doc:`../how-to/run-in-ci` for the
PowerShell form).

``drift-doctor remediate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cascade template truth into the derived models.

::

    drift-doctor remediate [--kind PREFIX]... [--dry-run] [--sync] [--converge]
                           [--model NAME] [--yes] [--interactive]
                           [--confirm-deletions] [--ref NAME]... [--add-missing]
                           [--digest-json FILE] [--backup] [--allow-stale]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--kind PREFIX``
     - Only findings of this kind (a dotted prefix, matched at a segment
       boundary as in ``detect``). Repeatable; it narrows
       ``allowlist.kinds`` and never widens it.
   * - ``--dry-run``
     - Compute every edit and print unified diffs; write nothing, not
       the models and not the ledger.
   * - ``--sync``
     - Also offer ``retire.*`` and purge items (deletions of objects
       provably retired from the template, or of an uncustomized
       category). Never on by default.
   * - ``--converge``
     - Re-detect and re-apply until a pass changes nothing, at most 4
       passes. With ``--dry-run`` it has no effect and the run says so
       (``note: --converge has no effect with --dry-run``).
   * - ``--model NAME``
     - Only the named derived model.
   * - ``--yes``
     - Apply without asking, but only batch-safe kinds, and only with
       at least one ``--kind``. Never deletes anything.
   * - ``--interactive``
     - Ask before every fix. This is the default on a terminal.
   * - ``--confirm-deletions``
     - With ``--sync``: the explicit second confirmation that lets
       deletions run without a terminal (for scheduled jobs). Without
       ``--sync`` it is refused (exit 2).
   * - ``--ref NAME``
     - Push only this template measure (bare name or ``Table[Measure]``;
       repeatable) to every model, where each model hosts it. Other
       drift is left alone.
   * - ``--add-missing``
     - With ``--ref``: also insert the measure into models that lack it
       (on the template's host table).
   * - ``--digest-json FILE``
     - Write the run's decision digest (what was retained, what needs a
       person, what owes a refresh) as JSON.
   * - ``--backup``
     - Copy each file to ``<name>.bak_<YYYYMMDD_HHMMSS>`` before its
       first write in the run; the copies are removed when the run
       succeeds (``backups: removed 1 safety copy``) and kept when
       anything failed. Never in a dry run.
   * - ``--allow-stale``
     - Proceed on a stale baseline, at the risk of misclassified drift.

.. warning::

   **Without a terminal,** ``remediate`` **applies nothing.** ``remediate``
   confirms every fix with a question (``y``/``n``, ``a`` = yes to the
   rest of the non-destructive ones, ``q`` = stop). A question needs a
   terminal. When standard input is not a terminal (a script, a pipe, a
   CI job, an IDE agent), the questions are disabled, every item is
   treated as a "no", and the run writes nothing: not the models, not
   the ledger. It says so once:

   ``note: stdin is not a terminal, so questions are disabled and every
   item is treated as 'no' (non-interactive). Pass --yes with --kind to
   apply batch-safe kinds.``

   The rules, in one place:

   - **On a terminal**, every fix is asked, and a deletion is flagged
     ``DESTRUCTIVE (deletes derived-model content)``.
   - **Without a terminal**, nothing is applied, and each item is
     counted under ``skipped_noninteractive``.
   - **With** ``--yes`` **and at least one** ``--kind``, the batch-safe
     kinds are applied without asking. A kind that is not batch-safe is
     skipped ("not batch-safe: it needs an interactive answer"), and a
     deletion is never applied (``skipped_destructive``). ``--yes``
     without ``--kind`` exits 2:
     ``ERROR: --yes requires an explicit --kind (it never applies every kind at once)``.
   - **With** ``--sync --confirm-deletions``, deletions run without a
     terminal. This is the only way a scheduled job deletes anything.

   The batch-safe kinds are listed in
   :doc:`drift-kinds-and-ledger`.

``--dry-run`` ends each ``[would apply]`` line with the treatment a
real run would give it: ``[asked; batch-safe under --yes]``,
``[asked]`` (a person must approve it), or
``[destructive: asked, never under --yes]``.

On a terminal, ``remediate`` also offers to delete a model's own extras
(``extra.measure``, ``extra.column``, ``relationship.extra``), one
question each, naming how many report references would break. A batch
run and a ``--yes`` run never do.

Each finding passes these checks, in order. The first that stops it
decides its status:

1. **Override**: a finding a ``fleet.yml`` override acknowledges is
   ``overridden`` and never applied.
2. **Advisory**: the model's own work is ``skipped`` (or offered for
   deletion on a terminal, above).
3. **No fix**: a kind with no automated fix is ``manual``.
4. **Allowlist**: the kind must be in ``allowlist.kinds``, or it is
   ``skipped``.
5. **Sync**: ``retire.*`` and purge kinds need ``--sync``, or they are
   ``skipped``.
6. **Coupling guard**: a retirement the model's own work depends on is
   ``blocked`` (decided at detect time, with the reason).
7. **Deletion**: a deletion is applied only with ``--sync`` and either
   a yes on a terminal or ``--confirm-deletions``; otherwise it is
   ``skipped_destructive``.
8. **Batch safety**: under ``--yes``, a kind that is not batch-safe is
   ``skipped``.
9. **Source divergence**: a change on a table that reads its own source
   view may be ``skipped_divergent``.
10. **Late override**: an override found at apply time is
    ``skipped_override``, so a stale finding never writes a declared
    divergence.
11. **Preconditions**: checked against the model as earlier fixes in the
    same run left it; an unmet one is ``auto_skipped_precondition``.
12. **Write guards**: the new content must be valid TMDL, must not
    touch a file only the model has (``OVERLAY``), and must not touch a
    file exempted under ``overrides.files``; a block that does not read
    back as written is ``failed`` and the file is restored.

Fixes run in dependency order, whatever the detection order:
``table.missing``, ``column.missing``, ``column.property_drift``,
``expression.drift``, ``expression.missing``, ``mapping_row.missing``,
``measure.renamed``, ``measure.missing``, ``measure.wrong_host``,
``measure.duplicate_host``, ``measure.expression_drift``,
``measure.property_drift``, ``relationship.missing``,
``relationship.modified``, ``relationship.casing_mismatch``,
``retire.relationship``, ``retire.measure``, ``retire.mapping_row``,
``retire.mapping_category``, ``retire.source_view``,
``retire.column``, ``retire.table``, the purge block, then
``retire.fieldparam_entry``, ``purge.ifilter_regen`` and
``retire.ifilter_regen``. The field-parameter and mapping-category
kinds follow in their own phase. A dry run tracks what it would have
added, so a relationship whose endpoint column is added earlier in the
same run shows as ``would-apply``.

Each outcome has a status: ``applied``, ``would-apply`` (dry run),
``skipped``, ``manual``, ``blocked``, ``auto_skipped_precondition``,
``overridden``, ``skipped_override``, ``skipped_divergent``,
``skipped_destructive``, ``skipped_noninteractive`` or ``failed``. The
summary line counts each, and the run ends with a
``── Sync summary (DRY-RUN|APPLIED):`` block: one line per fleet model
and a ``FLEET TOTAL`` line, each with six counters. Applied fixes are
appended to the ledger. After a run that applied something,
``<state_dir>/last_sync.json`` records per model what was applied; a
run that produced a decision writes ``<state_dir>/decision_digest.json``.
``remediate`` exits 0 on success, including "nothing to do", and 1 if
any fix failed.

``--ref``: push named measures
""""""""""""""""""""""""""""""""""

``--ref`` pushes exactly the named template measures to every model,
editing each model's own host table and keeping its lineage tag. It
follows the same terminal rule: without a terminal it needs ``--yes``.

::

    $ drift-doctor remediate --ref "Total Visits" --yes
    [applied] alpha: Total Visits — overwrite 'Total Visits' from the template
    [skipped] bravo: Total Visits — unchanged

    ── summary: applied=1 would-apply=0 skipped=1 failed=0

A name the template does not have exits 2 before anything is written:

::

    $ drift-doctor remediate --ref "No Such"
    Error: measure 'No Such' does not exist in the template; nothing was changed

``drift-doctor ratchet check`` and ``ratchet tighten``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fail CI when drift rises above recorded per-model floors.

::

    drift-doctor ratchet check   [--from-json FILE] [--allow-stale] [--total-only] [--include-advisory]
    drift-doctor ratchet tighten [--from-json FILE] [--allow-stale] [--total-only] [--allow-new] [--prune]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--from-json FILE``
     - Use a saved ``detect --json`` report. Without it, the command
       runs a full-fleet detection itself.
   * - ``--allow-stale``
     - Detect on a stale baseline.
   * - ``--total-only``
     - A separate mode: compare only each model's drift total (missing
       tables and measures, expression drift, missing columns, missing
       and modified relationships) with
       ``<state_dir>/drift_totals.json``, which
       ``ratchet tighten --total-only`` writes.
   * - ``--include-advisory``
     - ``check``: also fail on a ``retire.*`` finding that no sync can
       apply.
   * - ``--allow-new``
     - ``tighten``: record models that have no floor yet at their
       current counts.
   * - ``--prune``
     - ``tighten``: drop floors of models no longer in ``fleet.yml``
       (needs a full-fleet report).

The floors live in ``<state_dir>/floors.json``:

::

    {
      "last_tighten": {
        "at": "2026-10-22T16:30:14+00:00",
        "models": ["alpha", "bravo"],
        "scope": "fleet",
        "template_tree": null
      },
      "models": {
        "alpha": {"by_category": {"expression": 2, "measure": 4}, "total": 6},
        "bravo": {"by_category": {"column": 2, "mapping_row": 1, "relationship": 2, "table": 1}, "total": 6}
      },
      "template_tree": null,
      "updated_at": "2026-10-22T16:30:14+00:00",
      "version": 2
    }

(``template_tree`` is ``null`` here because the fleet was not in a git
work tree.)

The unit of a floor is the total plus the **kind head**, the text
before the first dot: ``measure.missing`` and
``measure.expression_drift`` both count toward ``measure``. A version 1
file (keyed by kind) is read as it is and rolled up on load, and the
next ``tighten`` rewrites it in head form. Any other ``version`` is
refused with exit 2:

::

    ERROR: /tmp/gym-fleet/.drift-doctor/floors.json: not a drift-doctor floors file (expected version 2 with a `models` mapping)

``check`` counts per model, in total and per head, every finding a
sync could act on, whatever ``allowlist.kinds`` says, minus overridden
findings, advisory and report-only kinds, and the model-intrinsic
regenerations (``ifilter.*``, ``visibility.*``,
``ffilter.coverage_gap``). It fails (exit 1) when a count exceeds the
floor or a model has no floor:

::

    [RISE] alpha: TOTAL rose 6 -> 7
    [RISE] alpha: category 'column' rose 0 -> 1
    [RISE] charlie: no floor recorded; record one with `drift-doctor ratchet tighten --allow-new`
    ...
    DRIFT RATCHET RED

A clean run lists every model's counts per head, then says so:

::

      alpha: expression 2 (expression.drift 2)
      alpha: measure 4 (measure.expression_drift 1, measure.missing 1, measure.property_drift 1, measure.wrong_host 1)
      ...
    no ledger-retired object resurrected
    ratchet: every gated model is at or below its floor.

``tighten`` sets every floor to ``min(floor, current)`` and never raises
one; with no floors file it seeds one at current counts. When no floor
moves it still records when it measured:
``floors unchanged; the measurement was recorded: <path>``.

``retire.*`` findings are **resurrections**: an object the ledger proves
was retired is still, or again, in a model. They are never counted into
a floor and always fail ``check`` by name, in their own block:

::

    RESURRECTION — ledger-retired objects are back (hard zero, never floored):
      alpha: retire.measure Visits[Peak Hour Visits]
      alpha: cascade it with `drift-doctor remediate --model alpha --kind retire --sync`, or declare a `retain` override
      ...
    DRIFT RATCHET RED — RESURRECTION

A floors file that grants a retirement allowance is refused, because a
floor may never license a resurrection:

::

    ERROR: alpha: the floors file grants a retire allowance (retire: 1); resurrections are hard zero. Remove the key and remediate the model instead (`drift-doctor remediate --model alpha --kind retire --sync`)

Both subcommands refuse (exit 2) a report with a schema version other
than 2, a ``--kind`` filter, or detection errors. A ``--model``-scoped
report is accepted: ``check`` compares only its models, and ``tighten``
lowers only their floors and carries the others forward unchanged;
``--prune`` needs a full-fleet report. Models with ``gating: advisory``
are listed in their own block and never fail ``check``, resurrections
included.

``drift-doctor audit``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Re-verify every applied fix in the ledger.

::

    drift-doctor audit [--model NAME] [--json]

For the latest ``remediated`` event per model, kind and object:

- a missing-object fix (``table.missing``, ``column.missing``,
  ``measure.missing``, ``mapping_row.missing``,
  ``relationship.missing``, ``measure.wrong_host``) must still be
  present (on the template's host, for a move);
- a ``retire.*`` removal must not have come back.

Each event is ``ok``, ``reverted``, ``superseded`` (a revival or a
``retain`` override now keeps the object, the template retired it
since, or an ``absent`` override now declares it) or ``error`` (the
model did not parse). Overwrite fixes are not audited; drift on them is
``detect``'s job. Exit 4 if anything was reverted, 3 on a parse error,
else 0.

::

    $ drift-doctor audit
    ── audit: checked=6 ok=6 reverted=0 superseded=0 error=0

``--json`` prints one object per event:

::

    [
      {
        "status": "superseded",
        "detail": "revived or retained since the removal",
        "ts": "2026-10-22T16:33:22+00:00",
        "model": "alpha",
        "kind": "retire.measure",
        "ref": "Classes[Class Fill Rate %]"
      }
    ]

``drift-doctor review``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Write a per-model checklist of everything routed to a person.

::

    drift-doctor review [--out REVIEW.md] [--allow-stale]

It runs detection plus a dry-run remediation with ``--sync`` semantics
(nothing is written) and lists, per model: blocked retirements, fixes
waiting on a precondition, measures on the wrong or a duplicate host,
advisories, and overrides in force. Default output: ``REVIEW.md``.

::

    $ drift-doctor review --out REVIEW.md
    5 review item(s) -> REVIEW.md

The file opens with the rule that anything recurring in it is a
missing decision, and a key of resolutions: (A) a ``fleet.yml``
override, (B) a ledger revival, (C) an edit to the derived model, (D) a
template fix, (E) a new allowlist entry.

``drift-doctor ledger``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Show the ledger, or record a manual revival.

::

    drift-doctor ledger [--json]
    drift-doctor ledger --revive REF --kind KIND [--model NAME] [--note TEXT]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--json``
     - Print the raw JSONL entries.
   * - ``--revive REF``
     - Cancel the retirement in force for ``REF`` (for example
       ``"Visits[Peak Hour Visits]"``, ``"Plan Map/legacy-gold"``,
       ``"Visits[PromoId] -> Promotions[PromoId]"``) so it is never
       removed again. Requires ``--kind``.
   * - ``--kind KIND``
     - The retirement kind: ``table``, ``column``, ``measure``,
       ``mapping_row``, ``mapping_category`` or ``relationship``.
   * - ``--model NAME``
     - Scope the revival to one derived model. Default: the whole
       fleet.
   * - ``--note TEXT``
     - The reason, stored on the event.

Reviving a ref with no retirement in force exits 1; it is usually a
typo, and a silent no-op would hide that.

``drift-doctor diff`` and ``drift-doctor freshness``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both write Markdown for a pull-request comment; both are shown at work
in :doc:`../how-to/run-in-ci`.

::

    drift-doctor diff --base FILE --head FILE --out FILE [--fleet FILE]
    drift-doctor freshness --base-ledger FILE [--head-ledger FILE] [--base-label TEXT]
                           [--body-file FILE] [--stale-flag-file FILE]

``diff`` compares two ``detect --json`` reports and writes the blast
radius: the objects the change adds to the fleet's drift and the ones
it resolves, how far each reaches, and the per-model count by kind
head. A report without a scope block, a scoped or kind-filtered
report, and (with ``--fleet``) a committed baseline that no longer
matches the live template each raise a warning in the report; none
fails the run. A report it cannot read exits 2.

``freshness`` compares the ledger a branch was cut from
(``--base-ledger``) with the main line's (``--head-ledger``, default
the fleet's own ledger) and reports each retirement the branch has not
seen that a derived model still carries. A retirement of a kind it
cannot check is listed as not checked, and the body then says the
merge is not known to be safe. It always exits 0.

The other commands
~~~~~~~~~~~~~~~~~~~~~

Each has its own ``--help``. Most edit files: they are dry runs unless
told otherwise, as the table says.

.. list-table::
   :header-rows: 1

   * - Command
     - What it does
   * - ``add-branch --measure M --sibling S [--model NAME]... [--yes]``
     - Clone each SWITCH arm of the sibling measure for the new one, one
       new line right below each sibling arm, in the selector helper
       table (``selector_branch.helper_file``). A dry run unless
       ``--yes``.
   * - ``enrichment report [--format markdown|json] [--registry]``
     - Render the last run's view-enrichment entries (or, with
       ``--registry``, the whole register): the source views that must
       gain columns spliced onto source-divergent tables.
   * - ``enrichment rescan [--model NAMES] [--registry FILE]``
     - Warn about register entries whose recorded columns are gone from
       the model. Advisory: exit 5 when any warning is printed; never
       writes.
   * - ``fieldparam retag --from A --to B --display D... FILES...``
     - Move the named live field-parameter rows from category ``A`` to
       category ``B``; only the category literal changes. Nothing is
       written unless every requested row is found under ``--from`` in
       every file.
   * - ``fleet check [--stamps FILE]``
     - Validate ``fleet.yml``, the per-model overlay files and, with
       ``--stamps``, a connection-parameter stamping table. Exit 2 on a
       configuration problem, 1 when the stamping table disagrees with
       the fleet.
   * - ``fleet connection MODEL``
     - Print ``PROJECT<TAB>BILLING<TAB>DATASET`` for the model, always
       three fields. An empty project means "keep the template's
       default"; the dataset defaults to ``<model id>_db``.
   * - ``fleet family FAMILY``
     - Print the ids of the family's members, sorted and
       comma-separated. An empty family exits 1: a zero must never pass
       silently.
   * - ``groups plan --drop G... [--model NAME|--all|--path DIR] [--json FILE]``
     - Read-only: which field groups and fact tables are exclusive to
       the dropped groups (safe to remove) and which are shared (kept,
       naming the survivors). Dead fact tables are always listed.
   * - ``groups annotate [--model NAME|--all|--path DIR] [--dry-run]``
     - Mirror the mapping table's groups as ``model.tmdl`` annotations,
       one per group, keeping human-written descriptions.
   * - ``groups drop --drop G... [--layer L]... [--apply] [--verify] [--verify-cmd CMD]``
     - Drop groups end to end, in dependency order: selector branches,
       measures, selector rows, annotation, gates, bookmarks, dead
       tables, then mapping rows last. ``--layer`` runs only the named
       layers. A dry run unless ``--apply``; ``--verify`` runs
       ``--verify-cmd`` (default ``tmdl-preflight check {model}``) per
       model afterwards. Takes ``--model``, ``--all`` or ``--path``.
   * - ``groups drop-table --tables T... [--apply]``
     - Drop tables and every surface they occupy: boolean sensors in
       other measures, relationships, model registration, the Q&A
       schema, report bindings, then the file. A dry run unless
       ``--apply``. Takes ``--model``, ``--all`` or ``--path``.
   * - ``mapping decode TABLE``
     - Print the row count, the category count and the rows per
       category of an encoded table file. Exit 2 when the file does not
       hold exactly one encoded string.
   * - ``mapping diff DERIVED TEMPLATE``
     - The categories the template has and ``DERIVED`` lacks (``-``),
       and the categories only ``DERIVED`` has (``+``).
   * - ``mapping union --template FILE --derived FILE --out FILE``
     - Write every template row followed by each derived-only row into
       ``--out`` (a table file holding exactly one encoded string), then
       read it back.
   * - ``overrides check``
     - Check that every file exemption protects something: it resolves
       in the template and in the declaring model, and the model's copy
       still differs. Exit 1 when any declaration is stale.
   * - ``overrides files --model M [--item ITEM]``
     - Print the model's exempt file patterns, one bare pattern per
       line.
   * - ``overrides is-exempt --model M PATH``
     - Exit 0 when ``PATH`` (relative to the model root) is exempt from
       the template cascade, 3 when it is not.
   * - ``purge --measure NAME... [--model NAMES|--all] [--table T] [--apply] [--yes]``
     - Remove named measures from the chosen models (comma-separated,
       or ``template``; ``--all`` is every fleet model, never the
       template), on whatever table hosts them. Blocked while something
       else still calls the measure; ``--table`` picks the host when a
       measure sits on several. A dry run unless ``--apply``; ``--yes``
       applies without a terminal, because the names authorize it.
   * - ``rename measure OLD NEW [--dry-run] [--yes] [--model TEXT]... [--old-label L] [--new-label L] [--format-arm MODEL=FORMAT]...``
     - Rename a measure in the template and every model: picker labels,
       the declaration, DAX references (text comparisons included) and,
       with pbi-plot-styler installed, report bindings. Asks once unless
       ``--yes``. Exit 1 when no model declares ``OLD``, 2 when a
       precision loss would remain (pass ``--format-arm``).
   * - ``renames check [--model NAME]``
     - Every non-empty measure rename in the map must point at a measure
       the model declares. Exit 1 when one does not.
   * - ``renames apply [--model NAME] [--dry-run] [--yes]``
     - Rewrite references to renamed measures and columns in every
       model. Asks once unless ``--yes``. The declarations are not
       renamed here; see ``rename measure``.
   * - ``retire OLD [--new NEW] [--drop] [--skip-dir DIR] [--yes]``
     - Retire a superseded measure in the template and every model:
       report bindings move to ``NEW`` first, the declaration goes last
       (``--drop`` deletes only the declaration and leaves bindings);
       refused while DAX still calls it. A dry run unless ``--yes``.

For example, on the example fleet:

::

    $ drift-doctor retire "Peak Hour Visits" --drop
    template: dry run — drop the declaration from Visits.tmdl; 0 report binding(s) stay
    alpha: dry run — drop the declaration from Visits.tmdl; 0 report binding(s) stay
    bravo: dry run — drop the declaration from Visits.tmdl; 0 report binding(s) stay
    ── 3 model(s) affected

    $ drift-doctor rename measure "Peak Hour Visits" "Evening Peak Visits" --dry-run
    template: labels 0 decl 1 dax 0 reports n/a
    alpha: labels 0 decl 1 dax 0 reports n/a
    bravo: labels 0 decl 1 dax 0 reports n/a
    total: labels 0 decl 3 dax 0 reports 0 arm 0
    note: pbi-plot-styler is not installed, so report references are neither counted nor rewritten.

``fleet.yml`` configuration
-------------------------------

One file configures a fleet. Every path is resolved relative to the
file's directory.

::

    version: 1                                  # required, must be 1

    template: template/GymChain.SemanticModel   # required, the golden model
    models:                                     # required, non-empty map
      alpha: derived/alpha/GymChain.SemanticModel        # short form
      bravo:                                             # long form
        path: derived/bravo/GymChain.SemanticModel
        gating: advisory                        # enforced (default) | advisory
        gating_reason: still being aligned to the template
        overrides:
          - object: Members[JoinDate]
            kind: expression                    # expression | absent | retain | extension
            reason: bravo reports dates day-first by contract
            owner: bravo-analytics              # optional
            added: 2026-10-12                   # optional

    mapping_tables:                             # optional, tables whose rows
      - Plan Map                                #   are diffed row by row

    state_dir: .drift-doctor                    # optional, default .drift-doctor

    allowlist:                                  # optional; an EMPTY allowlist means
      kinds: [...]                              #   nothing is ever remediated
      expressions: [...]

.. list-table:: Top-level keys
   :header-rows: 1

   * - Key
     - Meaning
   * - ``version``
     - Required, and must be ``1``.
   * - ``template``
     - Required. The template's ``*.SemanticModel`` folder.
   * - ``models``
     - Required, a non-empty map of model id to path, or to a long-form
       entry (below).
   * - ``state_dir``
     - Where the shared state lives. Default ``.drift-doctor``.
   * - ``mapping_tables``
     - Tables whose rows are diffed row by row (below).
   * - ``allowlist.kinds``
     - The kinds ``remediate`` may apply (below).
   * - ``allowlist.expressions``
     - The shared expressions compared for content (below).
   * - ``connection_parameters``
     - Expressions that hold per-model values. Reported by
       ``expression.missing`` with a hint, never written.
   * - ``connection.project``
     - The fleet-level default project for the connection contract.
   * - ``overlays.dir``
     - The per-model overlay folders. Default ``overlays``.
   * - ``families.growth.suffixes``
     - Folder suffixes that make a model a growth-family member (two or
       more). Default ``Growth.SemanticModel``,
       ``insights.SemanticModel``.
   * - ``metadata.total``
     - When present, must equal the number of model entries.
   * - ``count_floor.family_prefixes``
     - The axis-table families (default ``x-Selector``,
       ``x-Plot Specific``, ``y-Selector``, ``y-Plot Specific``). A
       missing axis table fails ``detect`` whatever ``allowlist.kinds``
       says.
   * - ``category_annotations``
     - ``Category_*`` annotations in ``model.tmdl`` must match the
       categories a model's mapping adds on top of the template's;
       ``baseline`` names a file of accepted exceptions.
   * - ``fieldparam_tables``, ``fieldparam``
     - Which tables are field parameters, their families, the
       placeholder table, the "no legend" row and the tables the row
       merge leaves alone.
   * - ``source_identity``
     - How a table's source view is read (``function``,
       ``db_parameter``). With the block, a table that reads another
       view than the template's is source-divergent.
   * - ``notify_command``
     - A shell command that receives the run's view-enrichment entries
       as JSON on standard input.
   * - ``incremental_refresh``
     - Which fact tables follow the template's incremental-refresh
       policy and window (``enabled``, ``fact_pattern``, ``exempt``).
   * - ``purge``
     - The pristine-category purge (``enabled``,
       ``infrastructure_fraction``), used by ``detect --sync`` and
       ``remediate --sync``. Off by default.
   * - ``protected_name_pattern``
     - A case-insensitive regular expression: names no removal path
       ever touches.
   * - ``grouping``, ``gates``, ``bookmarks``, ``measure_liveness``
     - How ``groups plan``, ``groups drop`` and ``groups annotate``
       read groups, field groups, selector rows, gate measures and
       bookmarks.
   * - ``column_purge``
     - Model-only columns on shared tables removed in a sync run
       (``column.purge_listed``), with exceptions.
   * - ``visibility``
     - The visibility rules: ``helper_prefixes`` replaces the built-in
       helper-name test, ``always_visible`` adds helper-named measures
       that stay visible.
   * - ``selector_branch.helper_file``
     - The table file ``add-branch`` edits. Default
       ``Helper Measures.tmdl``.
   * - ``renames``
     - The reviewed rename map: ``measures``, ``columns``,
       ``profiles``, ``pairing``, ``format_table``, ``format_family``.
   * - ``table_roles``
     - Which tables are facts (``fact``) or not (``dimension``,
       ``other``), overriding the naming conventions.
   * - ``ignore_columns``
     - Column names never reported as missing or extra.
   * - ``expression_drift_ignore``
     - Measure-name prefixes whose DAX and properties are not compared.

The tool repository's ``docs/fleet-yml.md`` gives the defaults and
sub-keys of each block.

Every model path, template included, must contain a ``definition/``
directory; loading fails loudly otherwise.

A long-form model entry accepts these keys, and no others: ``path``,
``gating``, ``gating_reason``, ``overrides``, ``secondary_models``,
``connection``, ``family``, ``source_divergent``, ``workspace``,
``rename_map``, ``visibility``, ``snapshots``, ``rename_profile``. Any
other key is an error.

.. list-table:: Long-form model keys
   :header-rows: 1

   * - Key
     - Meaning
   * - ``path``
     - Required. The model's ``*.SemanticModel`` folder.
   * - ``gating``
     - ``enforced`` (the default) or ``advisory`` (below).
   * - ``gating_reason``
     - Why the model is advisory and what re-gates it.
   * - ``overrides``
     - Declared, reviewed divergence (below).
   * - ``secondary_models``
     - More semantic models of the same entry, each
       ``{name, path, deviations}``; ``deviations`` is required (``[]``
       for an exact clone). They inherit the entry's gating, overrides
       and connection block.
   * - ``connection``
     - The declared warehouse target: ``project``, ``billing_project``,
       ``dataset``.
   * - ``family``
     - Explicit family membership.
   * - ``workspace``
     - ``{name, guid, tenant_id, verified}``. GUIDs are checked, and no
       two entries share a workspace GUID.
   * - ``source_divergent``
     - Tables declared source-divergent when the view cannot be read.
   * - ``rename_profile``
     - The ``renames.profiles`` entry this model uses instead of the
       default maps.

``gating``
~~~~~~~~~~~~~~

``enforced`` (the default) or ``advisory``. An advisory model is
detected, remediated and reported like any other, but its findings
never set the ``detect`` exit code and never fail ``ratchet check``.
Use it for a model that is being onboarded, or that is not shipping
yet, so it cannot hold the fleet gate shut.

``overrides``
~~~~~~~~~~~~~~~~~

Declared, reviewed divergence for one model: "this model differs from
the template on purpose", as data instead of tribal knowledge. In the
flat-list form, each entry has:

.. list-table::
   :header-rows: 1

   * - Key
     - Meaning
   * - ``object``
     - Required. A ref in the finding's format: ``Table``,
       ``Table[Object]``, ``Table/row_key``, an expression name, or a
       relationship signature ``From[col] -> To[col]``.
   * - ``kind``
     - Required. ``expression``, ``absent``, ``retain`` or
       ``extension``.
   * - ``reason``
     - Required, non-empty. An override without a reason cannot be
       reviewed.
   * - ``owner``
     - Optional. Who decided.
   * - ``added``
     - Optional. When it was decided.

.. list-table:: What each override kind acknowledges
   :header-rows: 1

   * - Kind
     - Meaning
     - Acknowledged finding kinds
   * - ``expression``
     - The model keeps its own definition of a shared object.
     - ``measure.expression_drift``, ``measure.property_drift``,
       ``column.property_drift``, ``expression.drift``,
       ``relationship.modified``, ``measure.wrong_host``
   * - ``absent``
     - The model deliberately lacks a template object. On a table, it
       also covers ``relationship.missing`` findings into that table.
     - ``table.missing``, ``column.missing``, ``measure.missing``,
       ``mapping_row.missing``, ``relationship.missing``,
       ``expression.missing``, ``expression.drift``
   * - ``retain``
     - The model deliberately keeps an object retired from the
       template, or one a purge would remove.
     - ``retire.table``, ``retire.column``, ``retire.measure``,
       ``retire.mapping_row``, ``retire.mapping_category``,
       ``retire.relationship``, ``purge.table``, ``purge.relationship``
   * - ``extension``
     - The model deliberately adds an object of its own to a shared
       table.
     - ``extra.column``, ``extra.measure``, ``purge.column``,
       ``purge.measure``

``overrides`` may instead be a mapping of **typed sections**, which
also covers objects the flat form cannot name. The flat list keeps
working.

.. list-table:: Typed override sections
   :header-rows: 1

   * - Section
     - Keys (besides ``reason``, ``owner``, ``added``)
     - Acknowledges
   * - ``measures``
     - ``object``, ``kind`` (``expression`` or ``absent``; ``absent``
       takes a bare name, meaning any table)
     - Expression drift or a missing measure.
   * - ``columns``
     - ``object`` (``Table[column]``), ``kind`` (``absent`` or
       ``extension``)
     - A missing column, or a declared derived-only column.
   * - ``expressions``
     - ``object``, ``kind`` (``expression`` or ``absent``)
     - The same for shared expressions.
   * - ``source_views``
     - ``table``, ``view``
     - The model's table reads its own view on purpose.
   * - ``tables``
     - ``name``
     - A retained table.
   * - ``relationships``
     - ``signature``
     - A retained relationship.
   * - ``fieldparam_entries``
     - ``category``, ``entry``
     - A retained field-parameter entry.
   * - ``mapping_rows``
     - ``category``, ``key``
     - A retained mapping row.
   * - ``mapping_categories``
     - ``category``
     - A retained mapping category.
   * - ``refresh_windows``
     - ``table``, ``kind`` (``window`` or ``absent``) and the window
       fields
     - A declared incremental-refresh window, or a declared absence.
   * - ``files``
     - ``path`` (a glob relative to the folder holding the model)
     - ``remediate`` never writes the file, and findings whose fix
       would touch it are reported as overridden.

Validation is loud, because a typo must never silently disable a gate.
At load time, unknown keys, a missing or empty ``reason``, an unknown
``kind`` or a missing ``object`` fail. At detect time, each ``object``
must resolve: ``expression`` against the template's measures, columns,
relationships and shared expressions; ``absent`` against anything the
template defines; ``retain`` against the ledger's retirement history.
An overridden finding is never remediated and never fails ``detect`` or
the ratchet, but it always prints as an ACK and is listed by
``review``.

``allowlist.kinds``
~~~~~~~~~~~~~~~~~~~~~~~

The drift kinds ``remediate`` may apply. Anything not listed is
detected and reported but never fixed. Entries are dotted prefixes,
matched at a segment boundary: ``measure`` allows every ``measure.*``
kind, ``measure.missing`` also allows ``measure.missing.*``, and
``measure.miss`` allows nothing. The allowlist never decides what
``detect`` reports or what the ratchet counts.

Every kind, with whether it can be fixed, whether ``--yes`` may apply
it and whether it needs ``--sync``, is in
:doc:`drift-kinds-and-ledger`. Two rules matter when choosing:

- The advisory kinds (``extra.measure``, ``extra.column``,
  ``relationship.extra``, ``extra.mapping_row``) have no fix: listing
  one changes nothing, because a model-only object is a person's
  decision.
- ``retire.*`` and the purge kinds are additionally gated behind
  ``--sync``: listing them is necessary but not sufficient. A deletion
  is never applied under ``--yes``; it needs a yes on a terminal, or
  ``--sync`` with ``--confirm-deletions``.

``allowlist.expressions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The named shared expressions (``expressions.tmdl`` blocks) whose
**content** is compared. A name that is not listed here is never
compared for content, so it can never be reported as
``expression.drift`` nor cascaded.

.. important::

   This list does **not** gate detection of a missing expression.
   Every expression the template declares and a model does not is
   reported as ``expression.missing``, whether or not the name is
   listed here. A name listed under ``connection_parameters`` is
   reported too, with the hint that a connection parameter is never
   written: copy the declaration from the template and set the model's
   own value.

``expressions.tmdl`` is a mixed file: it typically holds per-tenant
connection parameters (warehouse names, project ids, currencies)
alongside a small set of genuinely shared parameters (reporting window
dates, feature toggles). Cascading the whole file would point every
tenant at the template's data source, so name exactly the parameters
that are canonical in the template, and nothing else. Naming a
connection parameter under ``allowlist.expressions`` is a configuration
error.

``mapping_tables``
~~~~~~~~~~~~~~~~~~~~~~

Tables listed here get row-level treatment. Two shapes are supported:

- A plain DAX ``DATATABLE`` literal in the partition source. Each row,
  keyed by its first column value, is compared on its own. This enables
  ``mapping_row.missing`` (a template row a model lacks) and
  ``retire.mapping_row`` (a row retired from the template, removed from
  the models while sibling rows stay).
- A Desktop "Enter data" table, whose partition calls
  ``Binary.FromText`` with a base64, raw-deflate JSON payload. The tool
  decodes it and compares the rows by **(category, key)**. That adds
  ``mapping_category.missing`` (a whole template category the model
  lacks), ``extra.mapping_row`` (a model-only row, advisory) and
  ``retire.mapping_category`` (a category retired from the template,
  removed whole). ``drift-doctor mapping decode`` shows what such a
  table holds.

Rows that exist only in a derived model are never removed by a
cascade: a custom row is tenant customization, the same doctrine as an
extra measure.

State files
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - File
     - Role
     - Commit it?
   * - ``<state_dir>/baseline.json``
     - The committed template truth, written by ``capture``.
     - Yes
   * - ``<state_dir>/ledger.jsonl``
     - Append-only audit and retirement record.
     - Yes
   * - ``<state_dir>/floors.json``
     - Ratchet floors, written by ``ratchet tighten``.
     - Yes, if you use the ratchet
   * - ``<state_dir>/drift_totals.json``
     - The totals ``ratchet tighten --total-only`` records.
     - Yes, if you use ``--total-only``
   * - ``<state_dir>/last_sync.json``
     - The sync receipt: per model, what the last applying run applied.
       A run that applied nothing leaves the file byte-identical.
     - Yes
   * - ``<state_dir>/decision_digest.json``
     - The items the last run routed to a person. Written only when a
       run produced one.
     - Yes
   * - ``<state_dir>/view_enrichment_outstanding.json``
     - The view-enrichment register: the source views that must gain
       columns spliced onto source-divergent tables.
     - Yes
   * - ``<state_dir>/view_enrichment_report.json``
     - The last run's enrichment entries only.
     - No

The baseline, the ledger and the floors are shared fleet state:
detection and the ratchet only mean something when everyone, and CI,
reads the same files.

Line endings and byte-order marks
-------------------------------------

A fleet committed from Windows usually has CRLF line endings, and some
files start with a UTF-8 byte-order mark (BOM). Since 1.2.1, a model
with CRLF endings is handled like the same model with LF endings, and
every fixer writes an existing file back with its own line endings, so
the diff shows only the change that was asked for. That covers the
ordinary cascade, ``remediate --ref``, ``groups drop`` and
``groups drop-table`` (including CRLF report JSON), refresh policies,
and the restore after a failed read-back. The parser ignores a BOM.

Known limitations in 1.2.1:

- ``remediate --ref`` writes the file without its BOM, and a file
  restored after a failed read-back loses its BOM. Line endings are
  kept in both cases. The ordinary cascade keeps the BOM.
- A file the tool creates (for example the table file
  ``table.missing`` copies in) is written with LF endings, even when
  the template file and the rest of the model use CRLF.

If your fleet's ``.gitattributes`` normalizes line endings, git hides
both effects.

Design: why nothing cascades by default
---------------------------------------------

Every automated fix is authorized twice: the kind must be named in the
allowlist, and deletions additionally require ``--sync``. A fleet tool
that fixes everything it finds is a fleet-wide blast radius with a
progress bar. Detection can afford to be liberal; a false positive
costs a minute of reading. Remediation cannot: a wrong cascade lands
the same wrong edit in every model at machine speed. Default-deny
inverts the failure mode: a too-small allowlist leaves some drift
reported but unfixed, which is visible and safe; a too-large one lets
an unanticipated kind cascade before anyone decided whether it should,
which is silent and fleet-wide.

Start with the ``*.missing`` kinds; gaps are the safest cascades. Add
the overwrite kinds (``*_drift``) once the template is trusted, since
an overwrite assumes the template is correct, a process claim rather
than a tool claim. Add ``retire.*`` last, once the ledger has history
that has been reviewed. When a kind keeps getting ``--kind``-filtered
out of runs by hand, remove it from the allowlist; the policy should
live in the file, not in habit.

Design: why a run asks before it writes
---------------------------------------------

``remediate`` is a fleet-wide writer, so it asks. On a terminal, every
fix is a question, the question carries its position (``[3/12]``) and
flags a deletion as destructive, and ``a`` answers yes to the rest of
the non-destructive ones.

A question needs a terminal, and that is the whole reason a scripted
run changes nothing: the safe default for a run nobody is watching is
to write nothing, not to write everything. A scheduled job that wants
to fix something says which kind it is fixing (``--kind``), says that
it means it (``--yes``), and gets only the kinds that are safe to fix
without a person: never a deletion, and never a kind whose repair
regenerates a measure through another tool, changes a refresh policy
or changes visibility. Deletions need their own, separate consent
(``--sync --confirm-deletions``), because "may this run delete" and
"do I mean it" are two decisions.

Design: why the baseline must stay current
------------------------------------------------

``detect`` and ``remediate`` refuse to run against a stale baseline
(the template changed since the last capture), because a stale
baseline does not just produce slightly outdated results; it inverts
meanings. Suppose the template drops column ``cleaned`` from a table
and nobody recaptures: the baseline still lists ``cleaned`` as template
truth, models without it are reported as ``column.missing`` (the
correct state reported as drift), and the cascade tries to copy
``cleaned`` from a template that no longer has it. Meanwhile the drop
is never recorded as a retirement, so models that still carry the
column are never cleaned up.

A stale baseline is refused with **exit 2**, not 1, so a CI job that
reads exit 1 as "the model has drift" and exit 2 as "the run could not
be done" is right. Before 1.2.0 it exited 1, which made a missing
recapture look like a finding.

Detection could compare the models with the live template directly,
and deliberately does not: the ledger's ``retired`` events come from
comparing the previous baseline with a fresh snapshot, the only
trustworthy proof that an object used to be in the template, and the
baseline is a committed file, so what the fleet compares against is
under version control and reproducible on any machine or in CI.

``--allow-stale`` exists for forensics (comparing against a historical
baseline on purpose), and its name states what is being accepted. In
practice: recapture in the same commit as the template edit, read
capture's ``[ledger] retired ...`` lines before anyone runs ``--sync``,
and never hand-edit ``baseline.json`` to resolve a finding; a wrong
baseline means the template is wrong, so fix that and recapture.

Design: safe TMDL surgery
-----------------------------

Remediation edits TMDL as raw text blocks, never by parsing an object
into a data structure and writing it back. A parser keeps what it needs
to compare and drops the rest: lineage tags, annotations, format hints,
description lines, the exact formatting a desktop tool wrote.
Rebuilding TMDL from parsed fields would silently discard all of that.
So the engine locates an object's raw text block in the template file
and splices it into the model's file unchanged. A block inserted into a
model gets a fresh lineage tag, since a copied tag can collide with one
already present; a block overwriting an existing object keeps the
model's own tag, so identity stays stable and re-running the cascade
changes nothing.

The sharpest hazard is a bare multi-line DAX expression:

::

    measure 'Layered' =
            VAR _x = ...
            RETURN _x + 1                    # bare multi-line
        formatString: #,0

A single-line or fenced expression has an obvious "after the
expression" point to insert a property; the bare multi-line shape does
not. Inserting a property right after the declaration line puts it
between the ``=`` and the DAX, and the engine then reads the property
as part of the expression:

::

    measure 'Layered' =
        isHidden                              # now the first line of the expression
            VAR _x = ...

The measure fails to compile with a bare syntax error, and the edit
looks plausible in a diff. This exact bug once landed dozens of broken
measures across every model in a production fleet in a single
automated pass, discovered only when reports started failing.

The invariant is enforced twice. The writer, ``insert_property_line``,
classifies the expression shape and inserts after the whole body
(after the closing fence for fenced bodies, after the last body line
for bare multi-line ones), and never duplicates a property that is
already there. Independently, ``assert_no_property_injection`` scans
candidate content before any write and refuses it if a property line
appears before a bare multi-line expression body with body lines still
following. The guard runs inside ``assert_tmdl_valid``, so every code
path that writes TMDL passes it. Every candidate file is also checked
for tab-only indentation, balanced fences, and no duplicated
single-value property within one object.

Since 1.2.0, a property placed after an object's first annotation or
``changedProperty`` line is refused, and a DAX ``VAR`` name declared
twice in one scope is refused. Every inserted, overwritten or moved
block is read back after the edit and must equal what was intended;
when it does not, the file is restored and the fix is ``failed``. A
file a model has and the template does not is hashed before the run
writes anything: an ordinary fix that would write one fails with an
``OVERLAY`` error, and a change to one that no fix declared fails the
run (exit 1).
