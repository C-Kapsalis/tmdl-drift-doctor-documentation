CLI and configuration reference
====================================

Every command, flag, exit code, and the full ``fleet.yml`` schema, plus
the design decisions behind ``remediate`` that a reader needs before
trusting it against a real fleet.

Commands
-----------

All commands take ``--fleet PATH`` (default ``fleet.yml``).

.. list-table:: Exit codes, shared by every command
   :header-rows: 1

   * - Code
     - Meaning
   * - 0
     - Success: clean, nothing actionable, floors held, no reverts.
   * - 1
     - Actionable drift (``detect``), a ratchet rise (``ratchet
       check``), a failed fix (``remediate``), or a usage or
       configuration error (bad ``fleet.yml``, unresolvable override,
       stale baseline).
   * - 2
     - ``ratchet`` refuses its input: no floors file, or a report it
       cannot trust (wrong schema, kind-filtered, errored, or
       model-scoped for ``tighten``).
   * - 3
     - A derived model could not be parsed (``detect``, ``audit``).
   * - 4
     - ``audit`` found a reverted fix.

``drift-doctor capture``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Snapshot the template into ``<state_dir>/baseline.json`` and maintain
the retirement record.

::

    $ drift-doctor capture [--fleet fleet.yml]
    baseline written: .drift-doctor/baseline.json
      tables=5 columns=17 measures=9 relationships=3 mapping_rows=4 expressions=3

It parses the live template and writes the fresh snapshot as the
baseline (snapshot format 2: tables, columns, measures, shared
expressions, mapping rows, and relationships). If a previous baseline
exists, it diffs the two: objects present before and absent now become
``retired`` ledger events (kinds: ``table``, ``column``, ``measure``,
``mapping_row``, ``relationship``); actively retired objects present
again become ``revived`` events. A column or measure of a dropped table
is covered by the table's event, which lists the table's objects in an
``objects`` field. Relationships are always recorded, even when an
endpoint table was dropped, because that event is what later lets
``retire.table`` sweep the relationship out of a derived model.

A baseline written by an earlier version (format 1) is refused as stale
by ``detect`` and ``remediate``; run ``capture`` once to upgrade it. The
ledger is kept as is.

``drift-doctor detect``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read-only drift detection for every derived model.

::

    $ drift-doctor detect [--json] [--model NAME] [--kind PREFIX] [--allow-stale]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--json``
     - Emit the schema version 2 report (below).
   * - ``--model NAME``
     - Only the named derived model. An unknown name is an error.
   * - ``--kind PREFIX``
     - Only findings whose kind starts with the prefix (for example
       ``measure.``, ``retire.``).
   * - ``--allow-stale``
     - Proceed even if the template changed since the last capture.

A finding is **actionable** when its kind is in ``allowlist.kinds``, it
is not advisory, and no override acknowledges it. The same predicate
drives the ``detect`` exit code, the ratchet, and the review queue.
``detect`` exits 1 when any actionable finding sits on a model whose
``gating`` is not ``advisory``; findings on advisory models print but
never set the exit code. It exits 3 when a model could not be parsed
(the other models are still reported).

The text report tags each finding: ``[advisory]`` (never remediated),
``[not allowlisted]`` (reported, not actionable), and ``[blocked]`` (a
retirement that derived work depends on, with a ``blocked:`` line per
reason). Overridden findings are not listed as findings; they print as
an ACK block with the reason, owner, and date:

::

    declared divergence honored (overrides): 1 item(s)
      ACK measure.expression_drift   Visits[Total Visits]  [owner data-team, added 2026-09-30]
          reason: alpha excludes zero-minute visits by contract

A closing line counts ``actionable``, ``advisory``, ``overridden``, and
``errors``.

JSON report (schema version 2)
""""""""""""""""""""""""""""""""""

::

    {
      "schema_version": 2,
      "generated_at": "2026-10-12T09:00:00+00:00",
      "template_tree": "4b825dc6...",
      "scope": {"fleet": true, "models": ["alpha", "bravo"], "kind_filter": null},
      "errors": [],
      "models": {
        "alpha": {
          "gating": "enforced",
          "findings": [
            {"kind": "measure.missing", "model": "alpha",
             "ref": "Members[New Members #]", "template_value": null,
             "derived_value": null, "detail": "...", "advisory": false,
             "actionable": true}
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
     - The models the report covers.
   * - ``scope.kind_filter``
     - The ``--kind`` prefix, or ``null``.
   * - ``errors``
     - ``{"model", "error"}`` for every model that could not be parsed.
       A non-empty list means every count is understated.
   * - ``models.<name>.gating``
     - ``enforced`` or ``advisory``.
   * - ``models.<name>.findings``
     - Every finding not acknowledged by an override. Each carries
       ``kind``, ``model``, ``ref``, ``template_value``,
       ``derived_value``, ``detail``, ``advisory``, ``actionable``, and,
       when present, ``blocked`` (list of reasons).
   * - ``models.<name>.overridden``
     - The acknowledged findings, each with an ``override`` object
       (``object``, ``kind``, ``reason``, ``owner``, ``added``).
   * - ``models.<name>.counts``
     - ``actionable``, ``advisory``, ``overridden``,
       ``not_allowlisted``, and ``by_kind`` (actionable findings per
       kind).

This replaces the 1.0 output (a bare JSON array of findings). Consumers
of the old shape must read ``models.<name>.findings`` instead.

``drift-doctor remediate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cascade template truth into the derived models.

::

    $ drift-doctor remediate [--kind PREFIX] [--dry-run] [--sync] [--converge] [--model NAME] [--allow-stale]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--kind PREFIX``
     - Only remediate findings whose kind starts with the prefix.
   * - ``--dry-run``
     - Compute every edit and print unified diffs; write nothing, not
       the models, not the ledger.
   * - ``--sync``
     - Also apply ``retire.*`` removals. Without it, every retirement
       finding is skipped with a reason.
   * - ``--converge``
     - Re-detect and re-apply until a pass applies nothing, at most 4
       passes. Has no effect with ``--dry-run``, since nothing changes
       on disk between passes.
   * - ``--model NAME``
     - Only the named derived model.
   * - ``--allow-stale``
     - Proceed on a stale baseline, at the risk of misclassifying
       drift.

Every finding passes these gates, in order:

1. **Override**: a finding a ``fleet.yml`` override acknowledges is
   reported as ``overridden`` and never applied.
2. **Allowlist**: the kind must be named in ``allowlist.kinds``;
   advisory kinds have no fix at all.
3. **Sync**: ``retire.*`` needs ``--sync``.
4. **Coupling guard**: a retirement that derived-only work depends on
   is ``blocked`` (decided at detect time, with the reason).
5. **Preconditions**: checked at apply time, after the fixes earlier in
   the same run (see the drift-kind reference). An unmet one is
   ``auto_skipped_precondition``.
6. **Write guards**: the new content must be valid TMDL (tab-indented,
   balanced fences, no duplicate properties, no property inside a DAX
   body).

Fixes run in dependency order, whatever the detection order:
``table.missing``, ``column.missing``, ``column.property_drift``,
``expression.drift``, ``mapping_row.missing``, ``measure.missing``,
``measure.wrong_host``, ``measure.expression_drift``,
``measure.property_drift``, ``relationship.missing``,
``relationship.modified``, then ``retire.relationship``,
``retire.measure``, ``retire.mapping_row``, ``retire.column``,
``retire.table``. A dry run tracks what it would have added, so a
relationship whose endpoint column is added earlier in the same run
shows as ``would-apply``.

Each outcome has a status: ``applied``, ``would-apply`` (dry run),
``skipped`` (advisory, not allowlisted, no fix, or no ``--sync``),
``blocked``, ``auto_skipped_precondition``, ``overridden``, or
``failed``. The summary line counts each. Applied actions are appended
to the ledger. Exit codes: 0 on success, including "nothing to do"; 1
if any apply failed.

``drift-doctor ratchet check`` and ``ratchet tighten``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fail CI when drift rises above recorded per-model floors.

::

    $ drift-doctor ratchet check   [--from-json FILE] [--allow-stale]
    $ drift-doctor ratchet tighten [--from-json FILE] [--allow-stale] [--allow-new] [--prune]

.. list-table::
   :header-rows: 1

   * - Option
     - Effect
   * - ``--from-json FILE``
     - Use a saved ``detect --json`` report. Without it, the command
       runs a full-fleet detection itself.
   * - ``--allow-stale``
     - Detect on a stale baseline (only without ``--from-json``).
   * - ``--allow-new``
     - ``tighten``: record models that have no floor yet at their
       current counts.
   * - ``--prune``
     - ``tighten``: drop floors of models no longer in ``fleet.yml``.

The floors live in ``<state_dir>/floors.json``:

::

    {
      "version": 1,
      "updated_at": "2026-10-12T09:00:00+00:00",
      "template_tree": "4b825dc6...",
      "models": {
        "alpha": {"total": 6, "by_kind": {"measure.missing": 1, "...": 1}},
        "bravo": {"total": 6, "by_kind": {"relationship.missing": 1}}
      }
    }

``check`` counts actionable findings per model, total and per kind, and
fails (exit 1) when any count exceeds the floor, or a model has no
floor. It prints improved models as tightening candidates. ``tighten``
sets every floor to ``min(floor, current)`` and never raises one; with
no floors file it seeds one at current counts. Raising a floor is a
deliberate hand edit of the file, made in the change that justifies it.

``retire.*`` findings are **resurrections**: a ledger-retired object is
still or again in a model. They are never counted into a floor and
always fail ``check`` by name. To keep an ex-template object on
purpose, declare a ``retain`` override.

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
       ``"Visits[PromoId] -> Promotions[PromoId]"``). Requires
       ``--kind``.
   * - ``--kind KIND``
     - Retirement kind: ``table``, ``column``, ``measure``,
       ``mapping_row``, ``relationship``.
   * - ``--model NAME``
     - Scope the revival to one derived model. Default: fleet-wide.
   * - ``--note TEXT``
     - Human reason, stored on the event.

Reviving a ref with no active retirement is an error (exit 1); it is
usually a typo, and a silent no-op would hide that.

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
        overrides:
          - object: Members[JoinDate]
            kind: expression                    # expression | absent | retain
            reason: bravo reports dates day-first by contract
            owner: bravo-analytics              # optional
            added: 2026-10-12                   # optional

    mapping_tables:                             # optional, tables whose DATATABLE
      - Plan Map                                #   rows are diffed row-by-row

    state_dir: .drift-doctor                    # optional, default .drift-doctor
                                                #   baseline.json, ledger.jsonl, floors.json

    allowlist:                                  # optional, an EMPTY allowlist means
      kinds: [...]                              #   nothing is ever remediated
      expressions: [...]

Every model path, template included, must contain a ``definition/``
directory; loading fails loudly otherwise. A long-form model entry
accepts only ``path``, ``gating``, and ``overrides``; any other key is
an error.

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
     - Required. ``expression``, ``absent``, or ``retain`` (below).
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
values:

::

    table.missing            column.missing            column.property_drift
    measure.missing          measure.expression_drift  measure.property_drift
    measure.wrong_host       expression.drift          mapping_row.missing
    relationship.missing     relationship.modified
    retire.table             retire.column             retire.measure
    retire.mapping_row       retire.relationship

The advisory kinds (``extra.measure``, ``extra.column``,
``relationship.extra``, ``measure.duplicate_host``) have no applier by
design (see "Why nothing cascades by default", below). ``retire.*``
kinds are additionally gated behind ``--sync``: listing them here is
necessary but not sufficient. Prefix filtering on the command line
(``--kind measure.``) intersects with this list; the allowlist is the
outer boundary.

``allowlist.expressions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The named shared expressions (``expressions.tmdl`` blocks) that
participate in drift at all. This list gates detection as well as
remediation: an expression not named here is never compared, so it can
never be flagged or cascaded. ``expressions.tmdl`` is a mixed file: it
typically holds per-tenant connection parameters (warehouse names,
project ids, currencies) alongside a small set of genuinely shared
parameters (reporting window dates, feature toggles). Cascading the
whole file would repoint every tenant's data source, so name exactly
the parameters that are canonical in the template, and nothing else.

``mapping_tables``
~~~~~~~~~~~~~~~~~~~~~~

Tables listed here get row-level treatment: their partition source is
parsed as a DAX ``DATATABLE`` literal and each row, keyed by its first
column value, becomes a diffable unit. This enables ``mapping_row.missing``
(a template row a derived model lacks) and ``retire.mapping_row`` (a
row retired from the template, removed from derived models while
sibling rows survive). Rows that exist only in a derived model are left
alone; a custom row is tenant customization, the same doctrine as an
extra measure.

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

All three are shared fleet state: detection and the ratchet are only
meaningful when everyone, and CI, reads the same files.

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
