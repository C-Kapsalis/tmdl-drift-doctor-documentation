Drift kinds and ledger reference
=====================================

Every finding has a dotted ``kind``. The catalog below gives, for each
kind, what triggers it, what remediation does, the gates it must pass,
and the cases where cascading it is the wrong call. Then the ledger:
the append-only record that makes every retirement and every applied
fix reconstructable later.

Gates legend: A, must be in ``allowlist.kinds``; S, additionally
requires ``--sync``; none, advisory, never remediated.

Missing objects (template to derived)
-------------------------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Remediation
     - Gates
   * - ``table.missing``
     - A baseline table is absent from the derived model
     - Copy the template's table file (all lineage tags regenerated),
       register ``ref table`` in ``model.tmdl``. The partition source
       is the template's; review it.
     - A
   * - ``column.missing``
     - A baseline column is absent from a shared table
     - Splice the template's raw column block (fresh lineage tag)
     - A
   * - ``measure.missing``
     - A baseline measure is absent from a shared table
     - Splice the template's raw measure block, ``///`` description
       included (fresh lineage tag)
     - A
   * - ``mapping_row.missing``
     - A baseline mapping-table row (by row key) is absent
     - Insert the template's row tuple after the last existing row
     - A

The detector walks the committed baseline, not the live template, and
matches by name: tables by table name, columns and measures by name
within the same-named table, mapping rows by row key. Missing objects
are the safest cascade, purely additive; presence-but-divergence is a
different kind, below.

Do not cascade blindly when:

- **``table.missing``, and data sources differ.** The copied partition
  carries the template's source query; if the tenant's warehouse layout
  differs, cascade the table, then fix its partition before deploying.
- **``column.missing``, source-backed column.** The model validates but
  the next refresh fails if the tenant's source cannot supply the
  column. Check the source first.
- **The removal was deliberate.** A tenant may have removed the object
  on purpose. That is a policy conversation, not a bug: either leave
  the finding standing as a known exception, or narrow the fleet so
  the model is not compared. Do not remediate-and-revert in a loop.

Divergence on shared objects
----------------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Remediation
     - Gates
   * - ``measure.expression_drift``
     - Normalized DAX differs (comments, fences, and whitespace never
       count)
     - Overwrite the derived block with the template's raw block; the
       derived lineage tag is preserved
     - A
   * - ``measure.property_drift``
     - Expressions match but compared properties differ
       (``formatString``, ``isHidden``, ``displayFolder``, and so on)
     - Same block overwrite
     - A
   * - ``column.property_drift``
     - A shared column's compared properties differ (``dataType``,
       ``formatString``, ``summarizeBy``, and so on)
     - Same block overwrite
     - A
   * - ``expression.drift``
     - An allowlist-named shared expression differs or is absent
     - Replace or append exactly that expression block; everything
       else in ``expressions.tmdl`` stays byte-untouched
     - A (and named in ``allowlist.expressions``; gates detection too)

When a measure's expression and properties both drift, one
``measure.expression_drift`` finding is emitted and the block overwrite
fixes both. Property comparison uses a fixed set, ``dataType``,
``formatString``, ``displayFolder``, ``summarizeBy``, ``sourceColumn``,
``sortByColumn``, ``isHidden``; lineage tags, annotations, and other
tooling metadata are excluded on purpose, so a model resaved on another
machine does not light up the fleet. Expression comparison is
normalized: reformatting, reindenting, or adding a comment never
registers as drift, only a semantic-text change does.

Do not cascade blindly when:

- **The derived version is the correct one.** A large share of
  expression drift is an unback-ported fix. Read the diff
  (``--dry-run``) before cascading; if the derived model is right, fix
  the template, recapture, and cascade the other direction.
- **The logic is genuinely tenant-specific.** An auto-cascade keeps
  reverting a deliberate difference. Model it properly, a
  differently-named tenant-specific measure, or a parameter the
  template reads, rather than fighting the tooling.
- **A data-type or source disagreement is rooted in the source.** If
  the tenant's warehouse really serves a different type or column
  name, cascading the template's value breaks refresh; fix the source
  or accept the divergence explicitly.
- **Visibility is deliberately different per tenant.** If one tenant
  hides a measure for contractual reasons, an auto-cascade keeps
  unhiding it. Either tolerate the standing finding, or restructure so
  the difference lives outside the shared surface.

Extras (derived to template), advisory
--------------------------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Remediation
     - Gates
   * - ``extra.measure``
     - A derived measure on a shared table with no template counterpart
     - None; reported only
     - none
   * - ``extra.column``
     - A derived column on a shared table with no template counterpart
     - None; reported only
     - none

The template is a core, not a superset: every derived model must
contain it, but a derived model may legitimately extend beyond it, so
absence from the template is never by itself evidence that an object is
wrong. An extra might be tenant customization to keep, an experiment,
or debris from a template retirement, and presence alone cannot tell
those apart; only a recorded ``retired`` ledger event can, which is why
``extra.*`` has no applier at all, not "off by default," structurally
absent. Derived-only tables (with everything on them) and derived-only
mapping rows are not findings at all; whole-surface extensions are the
clearest form of legitimate customization.

Usually the right response to an advisory is nothing: a stable set of
extras per model is that tenant's custom surface, and ``detect`` exits
0 when only advisories remain. If an extra should become standard, add
it to the template and recapture; the finding disappears because the
object is now core. If an extra is genuinely debris, delete it by hand;
the suite does not do this for any object it cannot prove was once
template surface.

Retirements (ledger-driven deletions)
-------------------------------------------

Emitted only for objects with an active ``retired`` ledger event
(recorded automatically at recapture, cancelable by revival) that a
derived model still carries.

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Remediation
     - Gates
   * - ``retire.table``
     - Ledger-retired table still in the derived model
     - Delete the table file and deregister from ``model.tmdl``
     - A + S
   * - ``retire.column``
     - Ledger-retired column still on a shared table
     - Remove the column block
     - A + S
   * - ``retire.measure``
     - Ledger-retired measure still on a shared table
     - Remove the measure block
     - A + S
   * - ``retire.mapping_row``
     - Ledger-retired row still in a mapping table
     - Remove exactly that row tuple; sibling rows are kept
     - A + S

Additions are provable by presence in the template; removals cannot
work the same way, since "absent from the template" is also exactly
what legitimate tenant customization looks like. The ``retired``
ledger event carves out the one deletable population: objects provably
ex-template, witnessed by the recapture diff. Objects subsumed by a
bigger drop are not double-tracked; when a whole table is retired, its
measures and columns are covered by the single table entry, and a
column drop is tracked as its own ``Table[Column]`` retirement so it is
not lost inside a table-only inventory. A mapping-table row is tracked
individually rather than as part of the whole partition, since coarser
retirement kinds cannot express "one row leaves, the others stay":
table retirement would delete the survivors too, and treating the
whole partition as one blob would turn any row difference into an
all-or-nothing rewrite.

Do not sync blindly when:

- **Something in the derived model still references the object.** A
  derived-only measure whose DAX reads the retired table, a report
  visual bound to the retired measure, or tenant data still tagged with
  a retired mapping-row key. ``drift-doctor`` removes model objects; it
  does not rewrite reports or custom DAX. Search for references first,
  and sequence dependents before the object they depend on.
- **A tenant is contractually still using it.** Revive it for that
  model (``ledger --revive ... --model NAME``) so sync passes leave it
  alone, and keep everyone else on the removal path.
- **The retirement itself was a mistake.** Restore the object in the
  template and recapture; the ledger auto-stamps a fleet-wide revival
  and the channel stands down.
- **Mixed sync passes need an order.** When a retired measure
  references a retired column, remove the measure first; the suite
  already orders measure removals before column removals within one
  sync pass for this reason, so keep that order if scripting a custom
  one.

Exit-code semantics
-----------------------

``detect`` exits 1 when any non-advisory finding exists; advisories
alone exit 0. ``remediate`` exits 1 only when an apply failed.

Ledger format
=================

``<state_dir>/ledger.jsonl`` is one JSON object per line, append-only.
Fleet remediation mutates other people's models in bulk, and an
auditable record of it is the minimum standard: "why does tenant alpha
not have the evening-peak KPI" has to be answerable months later from
the record alone, retired from the template on this date, removed from
alpha by this run, these files touched. Reads fold the stream in
order; nothing is ever rewritten or deleted, so a corrupt line makes
every read fail loudly rather than being silently skipped or, worse,
silently mistargeting a removal.

Common fields
----------------

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Meaning
   * - ``ts``
     - string
     - UTC ISO-8601 timestamp, appended automatically
   * - ``event``
     - string
     - ``retired`` / ``revived`` / ``remediated``
   * - ``kind``
     - string
     - See per-event tables below
   * - ``ref``
     - string
     - Object reference (formats below)

Reference formats: tables use ``TableName``; columns and measures use
``Table[Object]``; mapping rows use ``Table/row_key``.

``retired``
--------------

Appended by ``capture`` when an object present in the previous baseline
is absent from the fresh snapshot. This is the proof of ex-template
existence that authorizes later removal.

::

    {"ts": "2026-07-17T09:30:11+00:00", "event": "retired", "kind": "measure",
     "ref": "Visits[Peak Hour Visits]", "source": "capture"}

``kind`` is one of ``table``, ``column``, ``measure``,
``mapping_row``. Mapping-row events additionally carry ``table`` and
``row_key``.

``revived``
--------------

Cancels an active retirement without erasing it. This is the escape
hatch when reality overrides a retirement: the template takes an
object back (auto-stamped fleet-wide at the next capture) or a human
records a deliberate re-add.

::

    {"ts": "...", "event": "revived", "kind": "measure",
     "ref": "Visits[Peak Hour Visits]", "source": "manual",
     "model": "alpha", "note": "alpha keeps its evening-peak KPI"}

.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``source``
     - ``capture`` (the object returned to the template) or ``manual``
       (``ledger --revive``)
   * - ``model``
     - Present on model-scoped revivals only; absent means fleet-wide
   * - ``note``
     - Optional human reason

``remediated``
------------------

Appended by ``remediate`` for every applied action, never in
``--dry-run``.

::

    {"ts": "...", "event": "remediated", "kind": "retire.measure",
     "model": "alpha", "ref": "Visits[Peak Hour Visits]",
     "action": "remove retired measure block",
     "files": [".../tables/Visits.tmdl"]}

Here ``kind`` is the finding kind (for example ``measure.missing``,
``retire.column``), ``action`` is the human-readable label of what was
done, and ``files`` lists every file the action touched.

The fold: how state is derived
------------------------------------

``active_retirements(model)`` walks the stream in order: ``retired``
puts ``(kind, ref)`` in force; ``revived`` removes it, for everyone if
the event has no ``model``, only for the matching model if it does; a
later ``retired`` for the same ``(kind, ref)`` puts it back in force.
``remediated`` events never affect the fold; they are pure audit.
Restoring a wrongly-removed object is always the same two steps: put
the block back, then revive the ref (see :doc:`../how-to/manage-a-fleet`).
The mistake and the correction both stay on the record. Dry runs write
neither models nor the ledger, so the ledger never claims something
that did not happen.
