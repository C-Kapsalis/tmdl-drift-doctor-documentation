CLI and configuration reference
================================

Every command, flag, exit code, and the full ``fleet.yml`` schema, plus
the design decisions behind ``remediate`` that a reader needs before
trusting it against a real fleet.

Commands
-----------

``drift-doctor`` has twenty commands. All of them take ``--fleet PATH``
(default ``fleet.yml``).

.. list-table::
   :header-rows: 1

   * - Command
     - What it does
   * - ``capture``
     - Snapshot the template into the baseline; record retirements and
       revivals.
   * - ``detect``
     - Detect drift in every derived model. Read-only.
   * - ``remediate``
     - Cascade template truth into the derived models (allowlist-gated).
   * - ``ratchet check`` / ``ratchet tighten``
     - Fail CI when drift rises above the recorded per-model floors; lower
       the floors.
   * - ``audit``
     - Re-verify every applied fix in the ledger.
   * - ``review``
     - Write a per-model checklist of everything routed to a human.
   * - ``ledger``
     - Show the remediation ledger, or record a manual revival.
   * - ``add-branch``
     - Clone each SWITCH arm of a sibling measure for a new one.
   * - ``diff``
     - Compare two detection reports and write what the change reaches.
   * - ``enrichment report`` / ``enrichment rescan``
     - Render, and re-check, the view-enrichment register.
   * - ``fieldparam retag``
     - Move field-parameter rows from one category to another.
   * - ``fleet check`` / ``fleet connection`` / ``fleet family``
     - Validate the configuration and answer questions about its models.
   * - ``freshness``
     - Warn that a branch predates retirements the main line has made.
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

.. list-table:: Exit codes, shared by every command
   :header-rows: 1

   * - Code
     - Meaning
   * - 0
     - Success: clean, nothing actionable, floors held, no reverts.
   * - 1
     - Actionable drift (``detect``), a ratchet rise (``ratchet
       check``), a failed fix (``remediate``), a reverted fix
       (``audit``), or a finding the command was asked to make and could
       not (``renames check``, ``overrides check``).
   * - 2
     - A usage or configuration error: a malformed or unresolvable
       ``fleet.yml``, an unknown ``--model``, a stale baseline, or a
       report ``ratchet`` cannot trust (wrong schema, kind-filtered,
       errored, or model-scoped for ``tighten``). **A stale baseline is a
       configuration problem, not a finding**, so it exits 2 and never
       1: a CI job reads it as "the run could not be done" rather than
       as "the model has drift".
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
the retirement record.

::

    $ drift-doctor capture [--fleet fleet.yml]
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=17 measures=9 relationships=3 mapping_rows=4 expressions=3

It parses the live template and writes the fresh snapshot as the
baseline (snapshot format **3**: tables, columns, measures, shared
expressions, mapping rows and relationships, plus ``provenance``,
``fact_tables``, ``table_source_views`` and ``metrics``). If a previous
baseline exists, it diffs the two: objects present before and absent
now become ``retired`` ledger events (kinds: ``table``, ``column``,
``measure``, ``mapping_row``, ``mapping_category``, ``relationship``);
actively retired objects present again become ``revived`` events. A
column or measure of a dropped table is covered by the table's event,
which lists the table's objects in an ``objects`` field. Relationships
are always recorded, even when an endpoint table was dropped, because
that event is what later lets ``retire.table`` sweep the relationship
out of a derived model. A template table re-pointed to another source
view is recorded once, as a ``source_view_change`` event.

A baseline written by an earlier version is refused as stale by
``detect`` and ``remediate``; run ``capture`` once to upgrade it. The
ledger is kept as is.

.. note::

   Snapshot format 3 is what v1.2.0 writes, and it refuses **any**
   other version, not only format 1. A baseline written by v1.1.0 is
   format 2, so it is stale too. The error names the formats:

   ``the committed baseline uses snapshot format 2, and this
   drift-doctor writes format 3 (it now compares shared expressions with
   their comments and records template metrics). Run `drift-doctor
   capture` once to upgrade it; the ledger is kept as is.``

``drift-doctor detect``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read-only drift detection for every derived model.

::

    $ drift-doctor detect [--json] [--model NAME] [--kind PREFIX] [--csv] [--sync] [--allow-stale]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--json``
     - Emit the schema version 2 report (below).
   * - ``--model NAME``
     - Only the named derived model. An unknown name is an error (exit
       2).
   * - ``--kind PREFIX``
     - Only findings whose kind starts with the prefix (for example
       ``measure.``, ``retire.``). The prefix matches at a segment
       boundary, so ``measure`` covers every ``measure.*`` kind and
       ``measure.miss`` covers nothing.
   * - ``--csv``
     - One CSV row per model, with the shape and the drift by bucket:
       ``model,tables,measures,fact_tables,filter_measures,user_facing,helpers,gaps,flagged,allowed,expr_drift,col_drift,rel_drift``.
   * - ``--sync``
     - Also report the sync-only channel (the pristine-category purge
       items).
   * - ``--allow-stale``
     - Proceed even if the template changed since the last capture.

A finding is **actionable** when its kind is in ``allowlist.kinds``, it
is not advisory, and no override acknowledges it. That predicate drives
the ``detect`` exit code and the review queue. (The ratchet counts
differently on purpose: it counts every finding a sync could act on,
whatever the allowlist says, so the allowlist decides what ``remediate``
writes and never what the ratchet counts. See below.)
``detect`` exits 1 when any actionable finding sits on a model whose
``gating`` is not ``advisory``; findings on advisory models print but
never set the exit code. It exits 3 when a model could not be parsed
(the other models are still reported).

The text report tags each finding: ``[advisory]`` (never remediated
without a person answering), ``[not allowlisted]`` (reported, not
actionable), and ``[blocked]`` (a retirement that derived work depends
on, with a ``blocked:`` line per reason). Overridden findings are not
listed as findings; they print as an ACK block with the reason, owner,
and date:

::

    declared divergence honored (overrides): 1 item(s)
      ACK measure.expression_drift   Visits[Total Visits]  [expression; owner data-team, added 2026-09-30]
          reason: alpha excludes zero-minute visits by contract

A closing line counts ``actionable``, ``advisory``, ``overridden``, and
``errors``, and the run ends with the cascade report: one ``[OK  ]`` or
``[GAP ]`` block per model, carrying the model's shape (``fact_tables``,
``f_measures``, ``user_facing``, ``helpers``) and what is missing, then
``Summary: <passing>/<total> models in cascade`` (with ``(N not
checked)`` when a model could not be looked at).

JSON report (schema version 2)
""""""""""""""""""""""""""""""""""

::

    {
      "schema_version": 2,
      "generated_at": "2026-10-12T09:00:00+00:00",
      "template_tree": "4b825dc6...",
      "scope": {"fleet": true, "models": null, "alternate_model": null,
                "targets": ["alpha", "bravo"], "kind_filter": null,
                "overrides": null},
      "errors": [],
      "models": {
        "alpha": {
          "source_divergent_tables": {},
          "gating": "enforced",
          "decisions": [],
          "findings": [
            {"kind": "measure.missing", "model": "alpha",
             "ref": "Members[New Members #]", "template_value": null,
             "derived_value": null, "detail": "...", "advisory": false,
             "remediable": true, "actionable": true}
          ],
          "overridden": [],
          "counts": {"actionable": 6, "advisory": 2, "overridden": 0,
                     "not_allowlisted": 0, "by_kind": {"measure.missing": 1}}
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
       ``null`` when the template is not in a git work tree. It pins the
       report to a committed template state.
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
     - The overrides file the run used. Always ``null`` in this
       version; the key is there so a run against another overrides
       file can say so.
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
     - Every finding not acknowledged by an override. Each carries
       ``kind``, ``model``, ``ref``, ``template_value``,
       ``derived_value``, ``detail``, ``advisory``, ``remediable``,
       ``actionable``, the kind-specific extras in ``data``, and, when
       present, ``blocked`` (list of reasons).
   * - ``models.<name>.overridden``
     - The acknowledged findings, each with an ``override`` object
       (``object``, ``kind``, ``reason``, ``owner``, ``added``).
   * - ``models.<name>.counts``
     - ``actionable``, ``advisory``, ``overridden``,
       ``not_allowlisted``, and ``by_kind`` (actionable findings per
       kind). The two counters can overlap: a kind that always gates
       (``model.count_below_template``, ``retire.stranded_ref``) counts
       as actionable even when the allowlist does not name it, and it
       also counts as not-allowlisted.

This replaces the 1.0 output (a bare JSON array of findings). Consumers
of the old shape must read ``models.<name>.findings`` instead.

``drift-doctor remediate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cascade template truth into the derived models.

::

    $ drift-doctor remediate [--kind PREFIX]... [--dry-run] [--sync] [--converge]
                             [--model NAME] [--yes] [--interactive]
                             [--confirm-deletions] [--ref NAME]... [--add-missing]
                             [--digest-json FILE] [--backup] [--allow-stale]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--kind PREFIX``
     - Only remediate findings whose kind starts with the prefix. May be
       repeated. The prefix matches at a segment boundary, so ``measure``
       covers every ``measure.*`` kind, ``measure.missing`` also covers
       ``measure.missing.*``, and ``measure.miss`` covers nothing.
   * - ``--dry-run``
     - Compute every edit and print unified diffs; write nothing, not
       the models, not the ledger.
   * - ``--sync``
     - Also offer ``retire.*`` and purge items (deletions of provably
       ex-template or uncustomised objects). Never on by default.
   * - ``--converge``
     - Re-detect and re-apply until a pass applies nothing, at most 4
       passes. Has no effect with ``--dry-run``, since nothing changes
       on disk between passes.
   * - ``--model NAME``
     - Only the named derived model.
   * - ``--yes``
     - Apply without asking, but only batch-safe kinds, and only with
       at least one ``--kind``. Never deletes anything.
   * - ``--interactive``
     - Ask before every fix. This is the default on a terminal.
   * - ``--confirm-deletions``
     - With ``--sync``: the explicit second confirmation that lets
       deletions run without a terminal.
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
     - Copy each file to ``<name>.bak_<timestamp>`` before its first
       write in this run; the copies are removed when the run succeeds
       and kept when anything failed.
   * - ``--allow-stale``
     - Proceed on a stale baseline, at the risk of misclassifying
       drift.

.. warning::

   **Without a terminal, ``remediate`` applies nothing.** This is the
   single most important thing to know about the command, and it
   changed in v1.2.0.

   ``remediate`` confirms every fix with a question (``y``/``n``,
   ``a`` = yes to the rest, ``q`` = stop). A question needs a
   terminal. When stdin is not a terminal — a script, a pipe, a CI job,
   an IDE agent — the questions are disabled, every item is treated as
   a "no", and the run writes nothing: not the models, not the ledger.
   The run says so once, on standard output:

   ``note: stdin is not a terminal, so questions are disabled and every
   item is treated as 'no' (non-interactive). Pass --yes with --kind to
   apply batch-safe kinds.``

   To apply from a script, name the kinds you mean and pass ``--yes``:

   ::

       $ drift-doctor remediate --yes --kind measure.missing
       [applied] alpha: measure.missing Members[New Members #] — insert measure block from template (fresh lineage tag)

   ``--yes`` without a ``--kind`` is a usage error (exit 2), because it
   would otherwise apply every allowlisted kind at once:

   ::

       $ drift-doctor remediate --yes
       ERROR: --yes requires an explicit --kind (it never applies every kind at once)

   ``--yes`` also never deletes anything. A deletion needs an
   interactive yes, or ``--sync`` together with ``--confirm-deletions``:

   ::

       $ drift-doctor remediate --kind retire. --sync
       note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
       [skipped] alpha: retire.measure Classes[Class Fill Rate %] — destructive: deletions are never applied under --yes or in batch mode; answer interactively, or pass --sync with --confirm-deletions

       $ drift-doctor remediate --kind retire. --sync --confirm-deletions
       [applied] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block

Every finding passes these gates, in order:

1. **Override**: a finding a ``fleet.yml`` override acknowledges is
   reported as ``overridden`` and never applied.
2. **Allowlist**: the kind must be named in ``allowlist.kinds``. An
   advisory kind has no automated fix, though a terminal run offers to
   delete a model's own extras, one question each.
3. **Sync**: ``retire.*`` and the purge kinds need ``--sync``.
4. **Coupling guard**: a retirement that derived-only work depends on
   is ``blocked`` (decided at detect time, with the reason).
5. **Preconditions**: checked at apply time, after the fixes earlier in
   the same run (see the drift-kind reference). An unmet one is
   ``auto_skipped_precondition``.
6. **Write guards**: the new content must be valid TMDL (tab-indented,
   balanced fences, no duplicate properties, no property inside a DAX
   body).

A seventh gate applies to the run rather than to the finding: without
a terminal nothing is written at all, and with ``--yes`` only the
batch-safe kinds are applied and no deletion ever is.

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
``retire.ifilter_regen``. The field-parameter and mapping kinds follow
in their own phase. A dry run tracks what it would have added, so a
relationship whose endpoint column is added earlier in the same run
shows as ``would-apply``.

Each outcome has a status: ``applied``, ``would-apply`` (dry run),
``skipped`` (advisory, not allowlisted, no fix, or no ``--sync``),
``manual`` (the kind has no automated fix), ``blocked``,
``auto_skipped_precondition``, ``overridden``, ``skipped_override``,
``skipped_divergent``, ``skipped_destructive``,
``skipped_noninteractive``, or ``failed``. The summary line counts
each, and the run ends with a ``── Sync summary (DRY-RUN|APPLIED):``
block: one line per model and a ``FLEET TOTAL`` line, each with the
same six counters. Applied actions are appended to the ledger. Exit
codes: 0 on success, including "nothing to do"; 1 if any apply failed.

``drift-doctor ratchet check`` and ``ratchet tighten``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fail CI when drift rises above recorded per-model floors.

::

    $ drift-doctor ratchet check   [--from-json FILE] [--allow-stale] [--total-only] [--include-advisory]
    $ drift-doctor ratchet tighten [--from-json FILE] [--allow-stale] [--total-only] [--allow-new] [--prune]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--from-json FILE``
     - Use a saved ``detect --json`` report. Without it, the command
       runs a full-fleet detection itself.
   * - ``--allow-stale``
     - Detect on a stale baseline (only without ``--from-json``).
   * - ``--total-only``
     - A separate mode: compare only each model's drift total with
       ``<state_dir>/drift_totals.json``, which
       ``ratchet tighten --total-only`` writes.
   * - ``--include-advisory``
     - ``check``: also fail on a ``retire.*`` finding that no sync can
       apply.
   * - ``--allow-new``
     - ``tighten``: record models that have no floor yet at their
       current counts.
   * - ``--prune``
     - ``tighten``: drop floors of models no longer in ``fleet.yml``.

The floors live in ``<state_dir>/floors.json``, in **version 2**:

::

    {
      "version": 2,
      "updated_at": "2026-10-12T09:00:00+00:00",
      "template_tree": "4b825dc6...",
      "last_tighten": {
        "at": "2026-10-12T09:00:00+00:00",
        "models": ["alpha", "bravo"],
        "scope": "fleet",
        "template_tree": "4b825dc6..."
      },
      "models": {
        "alpha": {"total": 5, "by_category": {"expression": 2, "measure": 3}},
        "bravo": {"total": 6, "by_category": {"column": 2, "mapping_row": 1,
                                               "relationship": 2, "table": 1}}
      }
    }

.. warning::

   The floors file changed shape in v1.2.0. The unit of the floor is
   now the **kind head** — the text before the first dot.
   ``measure.missing`` and ``measure.expression_drift`` both roll up to
   ``measure`` — so the per-kind floor is gone and ``by_kind`` is now
   ``by_category``.

   A committed version-1 file is not thrown away: it is read as-is and
   rolled up on load, so an existing floor is not lost, and the next
   ``tighten`` rewrites the file in head form. A file whose ``version``
   is neither 1 nor 2 is refused outright::

       ERROR: /…/.drift-doctor/floors.json: not a drift-doctor floors file (expected version 2 with a `models` mapping)

``check`` counts actionable findings per model, total and per kind
head, and fails (exit 1) when any count exceeds the floor, or a model
has no floor. A rise is reported in the ratchet's own words::

    [RISE] alpha: TOTAL rose 5 -> 6
    [RISE] alpha: category 'column' rose 0 -> 1
    ...
    DRIFT RATCHET RED

and a clean run lists every model against its floor, then says so::

      alpha: expression 2 (expression.drift 2)
      alpha: measure 3 (measure.expression_drift 1, measure.property_drift 1, measure.wrong_host 1)
      bravo: column 2 (column.missing 1, column.property_drift 1)
      ...
    no ledger-retired object resurrected
    ratchet: every gated model is at or below its floor.

``tighten`` sets every floor to ``min(floor, current)`` and never raises
one; with no floors file it seeds one at current counts. Raising a
floor is a deliberate hand edit of the file, made in the change that
justifies it.

``retire.*`` findings are **resurrections**: a ledger-retired object is
still or again in a model. They are never counted into a floor and
always fail ``check`` by name, in their own block::

    RESURRECTION — ledger-retired objects are back (hard zero, never floored):
      alpha: retire.measure Classes[Class Fill Rate %]
      alpha: cascade it with `drift-doctor remediate --model alpha --kind retire --sync`, or declare a `retain` override
      ...
    DRIFT RATCHET RED — RESURRECTION

To keep an ex-template object on purpose, declare a ``retain`` override.

Both subcommands refuse (exit 2) a report with a schema version other
than 2, a kind filter, or detection errors. ``tighten`` also refuses a
model-scoped report, since silence about the other models means
nothing; ``check`` accepts one and compares only its models. Models
with ``gating: advisory`` are listed in their own block and never fail
``check``, resurrections included.

``drift-doctor audit``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Re-verify every applied fix in the ledger.

::

    $ drift-doctor audit [--model NAME] [--json]

For the latest ``remediated`` event per model, kind, and object:

- a missing-object fix (``table.missing``, ``column.missing``,
  ``measure.missing``, ``mapping_row.missing``,
  ``relationship.missing``, ``measure.wrong_host``) must still be
  present (on the template's host, for a move);
- a ``retire.*`` removal must not have come back.

Each event is ``ok``, ``reverted``, ``superseded`` (the template retired
the object since, a revival or ``retain`` override now keeps it, or an
``absent`` override now declares it), or ``error`` (the model did not
parse). Overwrite fixes are not audited; drift on them is ``detect``'s
job. Exit 4 if anything was reverted, 3 on a parse error, else 0.
``--json`` prints one object per event with ``status``, ``detail``,
``ts``, ``model``, ``kind``, and ``ref``.

``drift-doctor review``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Write a per-model checklist of everything routed to a human.

::

    $ drift-doctor review [--out REVIEW.md] [--allow-stale]

It runs detection plus a dry-run remediation with ``--sync`` semantics
(nothing is written) and lists, per model: blocked retirements, fixes
waiting on a precondition, measures on the wrong or a duplicate host,
advisories, and overrides in force. The file opens with the doctrine:
anything that recurs here is a missing rule. Encode the decision once
(an override, a ledger revival, an allowlist entry, or a template fix)
instead of judging it again on every run. Default output:
``REVIEW.md``.

``drift-doctor ledger``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inspect the ledger, or record a manual revival.

::

    $ drift-doctor ledger [--json]
    $ drift-doctor ledger --revive REF --kind KIND [--model NAME] [--note TEXT]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--json``
     - Print raw JSONL entries.
   * - ``--revive REF``
     - Cancel the active retirement of ``REF`` (for example
       ``"Visits[Peak Hour Visits]"``, ``"Plan Map/legacy-gold"``,
       ``"Visits[PromoId] -> Promotions[PromoId]"`). Requires
       ``--kind``.
   * - ``--kind KIND``
     - Retirement kind: ``table``, ``column``, ``measure``,
       ``mapping_row``, ``mapping_category``, ``relationship``.
   * - ``--model NAME``
     - Scope the revival to one derived model. Default: fleet-wide.
   * - ``--note TEXT``
     - Human reason, stored on the event.

Reviving a ref with no active retirement is an error (exit 1); it is
usually a typo, and a silent no-op would hide that.

The other thirteen commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These commands were added in v1.2.0. Each has its own ``--help``; the
table gives the shape, and the tool's own ``README.md`` carries the
full command table with its exit codes.

.. list-table::
   :header-rows: 1

   * - Command
     - What it does
   * - ``add-branch --measure M --sibling S``
     - Clone each SWITCH arm of the sibling measure for the new one, one
       new line right below each sibling arm, in the selector helper
       table. ``--yes`` writes; the default is a dry run.
   * - ``diff --base B --head H --out FILE.md``
     - Compare two ``detect --json`` reports and write the blast radius
       as Markdown: the objects the change adds to the fleet's drift and
       the ones it resolves, how far each reaches, and what it means per
       model. The report is written for a CI comment, so a hidden marker
       line comes first and a later run edits the same comment in place.
   * - ``enrichment report [--format markdown|json] [--registry]``
     - Render the last run's (or the whole registry's) view-enrichment
       entries: the source views that must gain columns spliced onto
       divergent tables.
   * - ``enrichment rescan [--model NAMES] [--registry FILE]``
     - Warn about registry entries whose recorded columns are gone from
       the model. Advisory: exit 5 when any warning is printed, and
       nothing is ever written.
   * - ``fieldparam retag --from A --to B --display D FILES...``
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
     - Print ``PROJECT<TAB>BILLING<TAB>DATASET`` for the model. An
       empty project means "keep the template's default".
   * - ``fleet family FAMILY``
     - Print the ids of the family's members, sorted and
       comma-separated. An empty family is an error (exit 1): a zero
       must never pass silently.
   * - ``freshness --base-ledger FILE [--head-ledger FILE] [--base-label TEXT] [--body-file FILE] [--stale-flag-file FILE]``
     - Warn that a branch predates retirements the main line has made,
       and name the derived models that still carry them. Advisory by
       construction: the command always exits 0, because the ratchet is
       the blocking gate.
   * - ``groups plan --drop G [--model NAME|--all|--path DIR] [--json FILE]``
     - Read-only: which field groups and fact tables are exclusive to
       the dropped groups (safe to remove) and which are shared (kept,
       naming the survivors). Dead fact tables are always listed.
   * - ``groups annotate [--model NAME|--all|--path DIR] [--dry-run]``
     - Mirror the mapping table's groups as ``model.tmdl`` annotations
       (one per group; human-written descriptions are kept).
   * - ``groups drop --drop G [--layer L] [--apply] [--verify]``
     - Drop groups end to end: selector branches, measures, selector
       rows, annotation, gates, bookmarks, dead tables, then mapping rows
       last. A dry run unless ``--apply``.
   * - ``groups drop-table --tables T [--apply]``
     - Drop tables and every surface they occupy: boolean sensors in
       other measures, relationships, model registration, the Q&A
       schema, report bindings, then the file.
   * - ``mapping decode TABLE``
     - Print the row and category counts of an encoded table.
   * - ``mapping diff DERIVED TEMPLATE``
     - The categories the template has and ``DERIVED`` lacks (``-``), and
       the categories only ``DERIVED`` has (``+``).
   * - ``mapping union --template FILE --derived FILE --out FILE``
     - Write every template row followed by each derived-only row into
       the table, then read it back.
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
   * - ``purge --measure NAME [--model NAMES] [--all] [--table T] [--apply] [--yes]``
     - Remove named measures from the chosen models, on whatever table
       hosts them. Blocked while something else still calls the measure.
       A dry run unless ``--apply``; the names authorize the removal, so
       ``--yes`` applies it without a terminal.
   * - ``rename measure OLD NEW``
     - Rename a measure in the template and every model: picker labels,
       the declaration, DAX references (text comparisons included) and
       report bindings. Exit 1 when no model declares ``OLD``, 2 when a
       precision loss would remain (pass ``--format-arm``).
   * - ``renames check [--model NAME]``
     - Every non-empty measure rename must point at a measure the model
       declares. Exit 1 when one does not.
   * - ``renames apply [--model NAME] [--dry-run] [--yes]``
     - Rewrite references to renamed measures and columns in every model.
       The declarations are not renamed here; see ``rename measure``.
   * - ``retire OLD [--new NEW] [--drop] [--skip-dir DIR] [--yes]``
     - Retire a superseded measure in the template and every model:
       bindings move first, the declaration goes last; refused while DAX
       still calls it. A dry run unless ``--yes``.

``fleet.yml`` configuration
-------------------------------

One file configures a fleet. Every path is resolved relative to the
file's directory.

::

    version: 1                                  # required, must be 1

    template: template/GymChain.SemanticModel   # required, the golden model
    models:                                     # required, non-empty map
      alpha: franchises/alpha/GymChain.SemanticModel        # short form
      bravo:                                                # long form
        path: franchises/bravo/GymChain.SemanticModel
        gating: advisory                        # enforced (default) | advisory
        gating_reason: still being aligned to the template
        overrides:
          - object: Members[JoinDate]
            kind: expression                    # expression | absent | retain
            reason: bravo reports dates day-first by contract
            owner: bravo-analytics              # optional
            added: 2026-10-12                   # optional

    mapping_tables:                             # optional, tables whose rows
      - Plan Map                                #   are diffed row by row

    state_dir: .drift-doctor                    # optional, default .drift-doctor
                                                #   baseline.json, ledger.jsonl, floors.json

    allowlist:                                  # optional, an EMPTY allowlist means
      kinds: [...]                              #   nothing is ever remediated
      expressions: [...]

The tool's own ``docs/fleet-yml.md`` in the repository carries the
complete key-by-key reference, with every default. The keys below are
the ones a reader of this page is most likely to meet.

.. list-table:: Top-level keys
   :header-rows: 1

   * - Key
     - Meaning
   * - ``version``
     - Required, and must be ``1``.
   * - ``template``
     - Required. The template's ``*.SemanticModel`` folder.
   * - ``models``
     - Required, a non-empty map of name to path (or to a mapping).
   * - ``mapping_tables``
     - Tables whose rows are diffed row by row.
   * - ``state_dir``
     - Where the shared state lives. Default ``.drift-doctor``.
   * - ``allowlist``
     - ``kinds`` and ``expressions`` (below).
   * - ``connection_parameters``
     - The names of the expressions that hold per-model values. They
       are never written by a cascade.
   * - ``metadata``
     - ``metadata.total``, when present, must equal the number of model
       entries.
   * - ``families``
     - ``families.growth.suffixes``: the folder suffixes that make a
       model a growth-family member. At least two.
   * - ``connection``
     - The fleet-level default project for the connection contract.
   * - ``overlays``
     - ``overlays.dir``: the per-model overlay folders.
   * - ``source_identity``
     - How a table's source view is read. With the block, a table
       reading another view than the template's is source-divergent.
   * - ``incremental_refresh``
     - Which fact tables follow the template's incremental-refresh
       policy and window.
   * - ``purge``
     - The pristine-category purge (``detect --sync``,
       ``remediate --sync``).
   * - ``renames``
     - The reviewed rename map: ``measures``, ``columns``,
       ``profiles``, ``pairing``, ``format_table``, ``format_family``.
   * - ``fieldparam`` / ``fieldparam_tables``
     - Which tables are field parameters, and how their rows are laid
       out.
   * - ``visibility``
     - The visibility rules: ``helper_prefixes`` and
       ``always_visible``.
   * - ``grouping``, ``gates``, ``bookmarks``, ``measure_liveness``
     - How ``groups plan`` and ``groups drop`` read groups, field
       groups, selector rows, gate measures and bookmarks.
   * - ``column_purge``
     - The bookkeeping columns a sync run removes
       (``column.purge_listed``).
   * - ``protected_name_pattern``
     - Names no removal path ever touches.
   * - ``count_floor``
     - ``count_floor.family_prefixes``: the axis-table families. A
       missing axis table fails ``detect`` whatever
       ``allowlist.kinds`` says.
   * - ``category_annotations``
     - The ``Category_*`` annotations in ``model.tmdl`` must match the
       categories a model's mapping adds on top of the template's.
   * - ``notify_command``
     - Receives the run's view-enrichment entries as JSON on stdin.

Every model path, template included, must contain a ``definition/``
directory; loading fails loudly otherwise.

A long-form model entry accepts these keys, and no others; any other
key is an error:

``path``, ``gating``, ``gating_reason``, ``overrides``,
``secondary_models``, ``connection``, ``family``, ``source_divergent``,
``workspace``, ``rename_map``, ``visibility``, ``snapshots``,
``rename_profile``.

``gating``
~~~~~~~~~~~~~~

``enforced`` (the default) or ``advisory``. An advisory model is
detected, remediated, and reported like any other, but its findings
never set the ``detect`` exit code and never fail ``ratchet check``.
Use it for a model that is being onboarded, or that is not shipping
yet, so it cannot wedge the fleet gate shut.

``overrides``
~~~~~~~~~~~~~~~~~

Declared, reviewed divergence for one model: "this model differs from
the template on purpose," as data instead of tribal knowledge. Each
entry:

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
       ``extension`` (below).
   * - ``reason``
     - Required, non-empty. An override without a reason cannot be
       reviewed.
   * - ``owner``
     - Optional. Who decided.
   * - ``added``
     - Optional. When it was decided.

.. list-table:: What each kind acknowledges
   :header-rows: 1

   * - Kind
     - Meaning
     - Acknowledged finding kinds
   * - ``expression``
     - The model keeps its own definition of a shared object.
     - ``measure.expression_drift``, ``measure.property_drift``,
       ``column.property_drift``, ``expression.drift``,
       ``relationship.modified``
   * - ``absent``
     - The model deliberately lacks a template object. On a table, it
       also covers ``relationship.missing`` findings into that table.
     - ``table.missing``, ``column.missing``, ``measure.missing``,
       ``mapping_row.missing``, ``relationship.missing``,
       ``expression.drift``
   * - ``retain``
     - The model deliberately keeps an object retired from the
       template.
     - every ``retire.*`` kind
   * - ``extension``
     - The model deliberately adds a column of its own to a shared
       table.
     - ``extra.column``

``overrides`` may also be a mapping of **typed sections** in place of
the flat list, which keeps working: ``measures``, ``columns``,
``expressions``, ``source_views``, ``tables``, ``relationships``,
``fieldparam_entries``, ``mapping_rows``, ``mapping_categories``,
``refresh_windows`` and ``files``. A ``files`` entry exempts a whole
file from the template cascade; ``drift-doctor overrides check|files|is-exempt``
inspects those declarations.

Validation is loud, because a typo must never silently disable a gate.
At load time: unknown keys, a missing or empty ``reason``, an unknown
``kind``, or a missing ``object`` fail. At detect time, each ``object``
must resolve: ``expression`` against the template's measures, columns,
relationships, and shared expressions; ``absent`` against anything the
template defines; ``retain`` against the ledger's retirement history.
An overridden finding is never remediated and never fails ``detect`` or
the ratchet, but it always prints as an ACK and is listed by
``review``.

``allowlist.kinds``
~~~~~~~~~~~~~~~~~~~~~~~

The drift kinds ``remediate`` may apply. Anything not listed is
detected and reported but never fixed, and is not actionable. Valid
values are dotted prefixes, matched at a segment boundary: ``measure``
allows every ``measure.*`` kind, ``measure.missing`` also allows
``measure.missing.*``, and ``measure.miss`` allows nothing.

The kinds this documentation set discusses:

::

    table.missing            column.missing            column.property_drift
    measure.missing          measure.expression_drift  measure.property_drift
    measure.wrong_host       measure.duplicate_host    measure.renamed
    expression.drift         expression.missing
    mapping_row.missing      mapping_category.missing
    relationship.missing     relationship.modified     relationship.casing_mismatch
    category_annotation.undeclared
    fieldparam.row_missing   fieldparam.row_drift      fieldparam.blank_row
    fieldparam.schema_modernize  fieldparam.cross_level.<category>
    fieldparam.plot_specific_extra.<category>  fieldparam.dangling_row
    fieldparam.dangling_selector
    refresh_policy.missing   refresh_policy.window_drift  refresh_policy.invalid
    visibility.hidden_user_facing  visibility.helper_visible
    ifilter.coverage_gap     ffilter.coverage_gap
    retire.table             retire.column             retire.measure
    retire.mapping_row       retire.mapping_category    retire.relationship
    retire.source_view       retire.fieldparam_entry    retire.ifilter_regen
    purge.fieldparam_entry   purge.measure              purge.column
    purge.relationship       purge.zmap_row             purge.table
    purge.ifilter_regen      column.purge_listed

The tool emits fifty-eight kinds, and two more families whose suffix
is chosen at run time, so **the tool's own listing is the authority on
the full set**:

- the "Drift kinds" table in the tool's ``README.md``, which carries
  every kind with its trigger, its remediation and its gates;
- ``REMEDIABLE_KINDS`` and ``ADVISORY_KINDS`` in
  ``tmdl_drift_doctor/detect.py``, the two sets the allowlist is
  checked against, plus ``SYNC_ONLY_KINDS`` for the kinds that only
  appear in a ``--sync`` run and ``RETIREMENT_FINDING_KINDS`` for the
  deletions.

The advisory kinds (``extra.measure``, ``extra.column``,
``relationship.extra``, ``extra.mapping_row``) have no applier by
design (see "Why nothing cascades by default", below): listing one in
the allowlist changes nothing, because a model-only object is a human
decision. A terminal run does offer to delete a model's own extras, one
question each, and a batch run or a ``--yes`` run never does. One kind
that used to be advisory is not any more: ``measure.duplicate_host``
is fixable — the stale copy on the non-template host is removed, and the
copy on the template's host stays. Allowlist the kind to apply it.
``retire.*`` kinds and the purge kinds are additionally gated behind
``--sync``: listing them here is necessary but not sufficient. A
deletion is never applied under ``--yes``; it needs an interactive yes,
or ``--sync`` with ``--confirm-deletions``. The ``--kind`` filter on
the command line matches the same way, and intersects with this list;
the allowlist is the outer boundary.

``allowlist.expressions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The named shared expressions (``expressions.tmdl`` blocks) whose
**content** is compared. A name that is not listed here is never
compared for content, so it can never be flagged as
``expression.drift`` nor cascaded.

.. important::

   This list does **not** gate detection of a missing expression. Every
   expression the template declares and a model does not is reported as
   ``expression.missing``, whether or not the name is listed here. The
   list only scopes content comparison. (A name listed under
   ``connection_parameters`` is reported too, with the hint that a
   connection parameter is never written: copy the declaration from the
   template and set the model's own value.)

``expressions.tmdl`` is a mixed file: it typically holds per-tenant
connection parameters (warehouse names, project ids, currencies)
alongside a small set of genuinely shared parameters (reporting window
dates, feature toggles). Cascading the whole file would repoint every
tenant's data source, so name exactly the parameters that are canonical
in the template, and nothing else. Naming a connection parameter under
``allowlist.expressions`` is a configuration error.

``mapping_tables``
~~~~~~~~~~~~~~~~~~~~~~

Tables listed here get row-level treatment. Two shapes are supported:

- A plain DAX ``DATATABLE`` literal in the partition source. Each row,
  keyed by its first column value, becomes a diffable unit. This enables
  ``mapping_row.missing`` (a template row a derived model lacks) and
  ``retire.mapping_row`` (a row retired from the template, removed from
  derived models while sibling rows survive).
- A Desktop "Enter data" table, whose partition calls
  ``Binary.FromText`` with a base64 raw-DEFLATE JSON payload. The tool
  decodes it (``tmdl_drift_doctor.mapping_codec``) and compares the
  rows by **(category, key)**, not by row key. That adds
  ``mapping_category.missing`` (a whole template category the model
  lacks), ``extra.mapping_row`` (a model-only row, advisory) and
  ``retire.mapping_category`` (a category retired from the template,
  removed whole).

Rows that exist only in a derived model are left alone; a custom row is
tenant customization, the same doctrine as an extra measure.

State files
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - File
     - Role
     - Commit it?
   * - ``<state_dir>/baseline.json``
     - The committed template truth.
     - Yes
   * - ``<state_dir>/ledger.jsonl``
     - Append-only audit and retirement record.
     - Yes
   * - ``<state_dir>/floors.json``
     - Ratchet floors, written by ``ratchet tighten``.
     - Yes, if you use the ratchet
   * - ``<state_dir>/decision_digest.json``
     - The items the last run routed to a person.
     - Yes
   * - ``<state_dir>/last_sync.json``
     - The sync receipt: per model, what was applied, with that model's
       own stamps. A run that applied nothing leaves the file
       byte-identical.
     - Yes
   * - ``<state_dir>/view_enrichment_outstanding.json``
     - The view-enrichment register: the source views that must gain
       columns spliced onto divergent tables.
     - Yes
   * - ``<state_dir>/view_enrichment_report.json``
     - The last run's enrichment entries only.
     - No
   * - ``<state_dir>/drift_totals.json``
     - The drift totals ``ratchet tighten --total-only`` records.
     - Yes, if you use ``--total-only``

The baseline, the ledger and the floors are shared fleet state:
detection and the ratchet are only meaningful when everyone, and CI,
reads the same files.

Design: why nothing cascades by default
---------------------------------------------

Every automated fix is authorized twice: the kind must be named in the
allowlist, and deletions additionally require ``--sync``. A fleet tool
that fixes everything it finds is a fleet-wide blast radius with a
progress bar. Detection is cheap to be liberal with; a false positive
costs a minute of reading. Remediation is not: a wrong cascade lands the
same wrong edit in every model at machine speed. Default-deny inverts
the failure mode: a too-small allowlist leaves some drift reported but
unfixed, which is visible and safe; a too-large one lets an
unanticipated kind cascade before anyone decided whether it should,
which is silent and fleet-wide.

Start additive-only, with the ``*.missing`` kinds; gaps are the safest
cascades. Add the overwrite kinds (``*_drift``) once the template is
trusted, since an overwrite assumes the template is correct, a process
claim rather than a tool claim. Add ``retire.*`` last, once the ledger
has history that has been reviewed. When a kind keeps getting
``--kind``-filtered out of runs by hand, that is the signal to remove it
from the allowlist; the policy should live in the file, not in habit.

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
rewrites a whole report or regenerates a measure through another tool.

The rules, in one place:

- a terminal: every fix is asked; a deletion is asked again, and it
  says what it deletes.
- no terminal: nothing is applied. The run says so once.
- ``--yes``: batch-safe kinds only, and only with at least one
  ``--kind``. No deletions.
- ``--sync --confirm-deletions``: the explicit second confirmation that
  lets deletions run in a scheduled job.

Design: why the baseline must stay current
------------------------------------------------

``detect`` and ``remediate`` refuse to run against a stale baseline
(the template changed since the last capture), because a stale baseline
does not just produce slightly outdated results; it inverts meanings.
Suppose the template drops column ``cleaned`` from a table and nobody
recaptures: the baseline still lists ``cleaned`` as template truth,
derived models without it get flagged ``column.missing`` (a false
positive reporting the correct state as drift), and the missing-object
cascade tries to splice ``cleaned`` from a template that no longer
carries it. Meanwhile the drop is never recorded as a retirement, so
models that do still carry the column are never cleaned up.

A stale baseline is refused with **exit 2**, not 1. A CI job that
treats exit 1 as "the model has drift" and exit 2 as "the run could not
be done" is then right; the older behaviour, which exited 1, made a
missing recapture look like a finding.

The baseline also exists because detection could, in principle, diff
derived models against the live template directly, and deliberately
does not: the ledger's ``retired`` events come from the recapture diff
(previous baseline against fresh snapshot), the only trustworthy proof
that an object used to be template surface, and the baseline is a
committed artifact, so what the fleet compares against is in version
control and reproducible on any machine or in CI.

``--allow-stale`` exists for forensics, comparing against a historical
baseline on purpose, and its name states plainly what is being
accepted. In practice: recapture as part of the same commit as the
template edit, read capture's ``[ledger] retired ...`` output before
anyone runs ``--sync``, and never hand-edit ``baseline.json`` to
resolve a finding; a wrong baseline means the template is wrong, so fix
that and recapture.

Design: safe TMDL surgery
-----------------------------

Remediation edits TMDL as raw text blocks, never by parsing an object
into a dataclass and re-serializing it. A parser keeps what it needs to
compare and drops the rest: lineage tags, annotations, format hints,
description lines, the exact formatting a desktop tool wrote.
Rebuilding TMDL from parsed fields would silently discard all of that.
So the engine locates an object's raw text block in the template file
and splices it into the derived file, byte-faithful. A block inserted
into a model gets a fresh lineage tag, since a copied tag can collide
with one already present; a block overwriting an existing object keeps
the derived object's own tag, so identity stays stable and re-running
the cascade is a no-op.

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
measures across every model in a production fleet in a single automated
pass, discovered only when reports started erroring.

The invariant is enforced twice. The writer, ``insert_property_line``,
classifies the expression shape and inserts after the whole body
(after the closing fence for fenced bodies, after the last body line
for bare multi-line ones), and is idempotent: an already-present
property is never duplicated. Independently,
``assert_no_property_injection`` scans candidate content before any
write and refuses it if a property-keyword line appears before a bare
multi-line expression body with body lines still following. The guard
runs inside ``assert_tmdl_valid``, so every code path that persists
TMDL passes it, including block replacements that would otherwise look
safe by construction. Every candidate file content is also checked for
tab indentation only, balanced fences, and no duplicated single-value
property within one object; a guarded edit either persists valid TMDL
or persists nothing.

Two further guards came with v1.2.0. A property placed after an
object's first annotation or ``changedProperty`` line is refused, and a
DAX ``VAR`` name declared twice in one scope is refused. Every inserted,
overwritten or moved block is read back after the edit and must equal
what was intended. A file a model has and the template does not is
hashed before the run writes anything: an ordinary fix that would
write one fails with an ``OVERLAY`` error, and a change to one that no
fix declared fails the run (exit 1).
