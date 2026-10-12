Drift kinds and ledger reference
=====================================

Every finding has a dotted ``kind``. The catalog below gives, for each
kind, what triggers it, what remediation does, the gates it must pass,
and the cases where cascading it is the wrong call. Then the ledger:
the append-only record that makes every retirement and every applied
fix reconstructable later.

Gates legend: A, must be in ``allowlist.kinds``; S, additionally
requires ``--sync``; none, advisory, never remediated. Any finding can
also be acknowledged per model by a ``fleet.yml`` override, which
prints it as an ACK and never remediates it (see
:doc:`cli-and-configuration`).

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
matches by name: tables by table name, columns by name within the
same-named table, mapping rows by row key. Measures are matched by name
across the whole model, because the engine requires measure names to be
unique model-wide: a template measure found on another table is
``measure.wrong_host`` (below), never ``measure.missing``, so a name
that already exists anywhere is never inserted a second time. Missing
objects are the safest cascade, purely additive; presence-but-divergence
is a different kind, below.

Do not cascade blindly when:

- **``table.missing``, and data sources differ.** The copied partition
  carries the template's source query; if the tenant's warehouse layout
  differs, cascade the table, then fix its partition before deploying.
- **``column.missing``, source-backed column.** The model validates but
  the next refresh fails if the tenant's source cannot supply the
  column. Check the source first.
- **The removal was deliberate.** A tenant may have removed the object
  on purpose. That is a policy conversation, not a bug: record it as an
  ``absent`` override with its reason, so the finding becomes an ACK
  instead of standing debt. Do not remediate-and-revert in a loop.

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

Normalization details, applied to measure DAX and to shared M
expressions alike:

- ``//``, ``--``, and ``/* */`` comments are stripped only outside
  string literals and quoted identifiers, so a changed
  ``"https://..."`` literal is real drift, not a comment.
- ``meta [k = v, ...]`` records are canonicalized: items split,
  trimmed, spaced as ``k = v``, and sorted. Power BI Desktop reorders
  these bags on save; the order carries no meaning, the values do.
- Fence markers and runs of whitespace collapse.

Do not cascade blindly when:

- **The derived version is the correct one.** A large share of
  expression drift is an unback-ported fix. Read the diff
  (``--dry-run``) before cascading; if the derived model is right, fix
  the template, recapture, and cascade the other direction.
- **The logic is genuinely tenant-specific.** An auto-cascade keeps
  reverting a deliberate difference. Model it properly, a
  differently-named tenant-specific measure, or a parameter the
  template reads; when it must stay, declare an ``expression``
  override rather than fighting the tooling.
- **A data-type or source disagreement is rooted in the source.** If
  the tenant's warehouse really serves a different type or column
  name, cascading the template's value breaks refresh; fix the source
  or accept the divergence explicitly.
- **Visibility is deliberately different per tenant.** If one tenant
  hides a measure for contractual reasons, an auto-cascade keeps
  unhiding it. Either tolerate the standing finding, or restructure so
  the difference lives outside the shared surface.

Measure hosts
-----------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Remediation
     - Gates
   * - ``measure.wrong_host``
     - A template measure is absent from its template host table but
       present on exactly one other table of the derived model
     - Move the derived block verbatim to the template's host: DAX,
       properties, and lineage tag untouched. The destination is
       written first, so an interruption leaves a detectable duplicate,
       never a lost measure. A body that also differs surfaces as
       ``measure.expression_drift`` on the next detect; ``--converge``
       picks it up in the same invocation.
     - A
   * - ``measure.duplicate_host``
     - The derived model carries a template measure's name on more than
       one table (the template's host plus another, or two non-host
       tables). The engine will not load such a model.
     - None; reported only. Remove the stale copy by hand.
     - none

A move waits (precondition) while the template's host table is missing
from the model, while the host already carries the name, or while any
DAX references the measure qualified by its old host
(``'Members'[Visits per Member]``), since the move would leave that
reference dangling. Bare ``[Visits per Member]`` references are
host-independent and survive the move.

Do not cascade blindly when:

- **``measure.wrong_host``, and something outside the model names the
  old host.** Report visuals and other models that bind the measure
  through ``Members`` lose it after the move. The tool checks DAX inside
  the model, not reports; search them first.
- **``measure.wrong_host``, and the host was chosen on purpose.** A
  tenant may keep a measure on another table for its display folder,
  perspective, or field-list layout. Declare that with an ``expression``
  override rather than letting the move repeat.
- **``measure.duplicate_host``.** Deciding which copy is stale is a
  human call: compare the two bodies, keep the one that matches the
  template (or the one reports bind to), and delete the other.

Relationships
-----------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Remediation
     - Gates
   * - ``relationship.missing``
     - A template relationship's signature is absent from the derived
       ``relationships.tmdl``
     - Append the template's raw block (created if the file is absent).
       The template's block name is kept unless it collides with a
       derived one, then a fresh GUID is used.
     - A
   * - ``relationship.modified``
     - The signature exists but compared properties differ
     - Overwrite the derived block with the template's; the derived
       block name (GUID) is kept
     - A
   * - ``relationship.extra``
     - A derived relationship between two template tables with no
       template counterpart
     - None; reported only
     - none

Identity is the field signature ``FromTable[col] -> ToTable[col]``.
Block names, which are usually GUIDs that differ per model and change
when Desktop recreates a relationship, never participate. The compared
properties are ``fromCardinality``, ``toCardinality``, ``isActive``,
``crossFilteringBehavior``, ``securityFilteringBehavior``, and
``relyOnReferentialIntegrity``, each normalized to its engine default
when omitted, so ``isActive: true`` written out equals a block that
leaves it implicit. A relationship touching a derived-only table is not
a finding. ``relationship.missing`` waits (precondition) until both
endpoint columns exist in the model or are added earlier in the same
run.

Do not cascade blindly when:

- **``relationship.missing``, and the tenant's data cannot honor it.**
  A many-to-one relationship needs unique keys on the one side; if the
  tenant's data has duplicates, or the new relationship creates an
  ambiguous filter path with one of the tenant's own, the model fails
  to refresh or silently picks a path. Check the keys and the existing
  paths first.
- **``relationship.modified``, and the difference is deliberate.**
  Bidirectional filtering set for row-level security, or an inactive
  relationship a tenant activated for its own reports, is a decision,
  not drift. Declare it with an ``expression`` override.
- **``relationship.extra``.** A tenant-built relationship between
  shared tables is usually customization. Leave it, or add it to the
  template if it should be standard.

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
     - Delete the table file, deregister from ``model.tmdl``, and remove
       the template-owned or ledger-retired relationships touching it
     - A + S
   * - ``retire.column``
     - Ledger-retired column still on a shared table
     - Remove the column block and the template-owned or ledger-retired
       relationships using it
     - A + S
   * - ``retire.measure``
     - Ledger-retired measure still on a shared table
     - Remove the measure block
     - A + S
   * - ``retire.mapping_row``
     - Ledger-retired row still in a mapping table
     - Remove exactly that row tuple; sibling rows are kept
     - A + S
   * - ``retire.relationship``
     - Ledger-retired relationship (by signature) still in the derived
       model. Not emitted when an endpoint table or column has its own
       retirement finding, which sweeps the relationship instead.
     - Remove the relationship block
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

The coupling guard
~~~~~~~~~~~~~~~~~~~~~~

A retirement removes provably ex-template surface, but derived work can
still depend on it. ``retire.table``, ``retire.column``, and
``retire.measure`` are **blocked** (status ``blocked``, with the reason
on the finding and in ``detect`` output) when any of these depends on
the object:

- a derived-only measure or calculated column whose DAX references it
  (the scan is string-aware: references inside strings and comments do
  not count);
- a derived-only relationship touching it (template-owned and
  ledger-retired relationships are removed with it instead);
- a column whose ``sortByColumn`` is the retired column;
- a hierarchy level built on the retired column;
- for a table: a measure or column on that table that was not part of
  the table when it left the template (the table's ``retired`` event
  lists its objects), that is, the derived model's own work.

A blocked retirement stays actionable: the model still carries a
retired object, and a person decides. Remove or rewrite the dependent,
or keep the object with a ``retain`` override or a ledger revival.

Template-owned or ledger-retired dependents do not block; their own fix
resolves them. Whether that fix has landed is the retirement's
apply-time precondition: a template measure still reading a retired
column in the derived model must be overwritten first (earlier in the
same run, which the dependency order arranges when the kind is
allowlisted), or the removal is ``auto_skipped_precondition``.

Do not sync blindly when:

- **Something outside the model still references the object.** The
  guard sees DAX, relationships, sort-by columns, and hierarchies inside
  the model. It does not see report visuals bound to a retired measure,
  or tenant data still tagged with a retired mapping-row key.
  ``drift-doctor`` removes model objects; it never rewrites reports.
  Search them first.
- **``retire.relationship``, and a derived-only measure activates it.**
  ``USERELATIONSHIP`` names the two columns, not the relationship, and
  the guard does not treat it as a dependency of the relationship.
  Search the model for ``USERELATIONSHIP`` on those columns before
  syncing.
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

Preconditions
-----------------

Each fix declares what must already be true in the derived model when
it runs. They are evaluated at apply time, against the model as earlier
fixes in the same run left it (a dry run tracks what it would have
added or removed):

.. list-table::
   :header-rows: 1

   * - Kind
     - Precondition
   * - ``table.missing``
     - None of the table's template measures already exists elsewhere
       in the model (the copy would duplicate a model-global name).
   * - ``measure.missing``, ``measure.expression_drift``
     - Every table, column, and measure the template DAX references
       exists in the model or is added earlier in the run.
   * - ``measure.wrong_host``
     - The host table exists, does not already carry the name, and no
       DAX references the measure by its old host.
   * - ``relationship.missing``
     - Both endpoint columns exist or are added earlier in the run.
   * - ``retire.table``, ``retire.column``, ``retire.measure``
     - Nothing in the model still references the object (template-owned
       dependents fixed, ledger-retired ones removed).

An unmet precondition is ``auto_skipped_precondition`` with the reason.
Fixes run in dependency order (tables, columns, expressions, mapping
rows, measures, relationships, then retirements), so most chains
complete in one pass. When a fix only becomes visible after another
lands (a moved measure whose body also differs), ``remediate
--converge`` re-detects and re-applies until nothing changes, at most
four passes.

Exit-code semantics
-----------------------

``detect`` exits 1 when any actionable finding exists on a model whose
gating is not ``advisory``. Actionable means allowlisted, not advisory,
and not acknowledged by an override; advisories, non-allowlisted kinds,
and overridden findings alone exit 0. ``detect`` exits 3 when a model
could not be parsed. ``remediate`` exits 1 only when an apply failed.
``ratchet check`` exits 1 on a rise or a resurrection and 2 on an
untrusted report; ``audit`` exits 4 on a reverted fix. The full table is
in :doc:`cli-and-configuration`.

Ledger format
-----------------

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
~~~~~~~~~~~~~~~~

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
``Table[Object]``; mapping rows use ``Table/row_key``; relationships use
their field signature ``From[col] -> To[col]`` (for example
``Visits[PromoId] -> Promotions[PromoId]``).

``retired``
~~~~~~~~~~~~~~

Appended by ``capture`` when an object present in the previous baseline
is absent from the fresh snapshot. This is the proof of ex-template
existence that authorizes later removal.

::

    {"ts": "2026-07-17T09:30:11+00:00", "event": "retired", "kind": "measure",
     "ref": "Visits[Peak Hour Visits]", "source": "capture"}

``kind`` is one of ``table``, ``column``, ``measure``,
``mapping_row``, ``relationship``. Mapping-row events additionally
carry ``table`` and ``row_key``. Table events carry ``objects``, the
``Table[Object]`` refs of the columns and measures the table held when
it left the template; the coupling guard uses it to tell template-era
objects from the derived model's own work. A relationship is recorded
even when its endpoint table was dropped in the same capture.

``revived``
~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~

Appended by ``remediate`` for every applied action, never in
``--dry-run``.

::

    {"ts": "...", "event": "remediated", "kind": "retire.measure",
     "model": "alpha", "ref": "Visits[Peak Hour Visits]",
     "action": "remove retired measure block",
     "files": [".../tables/Visits.tmdl"]}

Here ``kind`` is the finding kind (for example ``measure.missing``,
``retire.column``), ``action`` is the human-readable label of what was
done, and ``files`` lists every file the action touched. For
``measure.wrong_host`` the ``ref`` is the template location
(``Visits[Visits per Member]``), and the destination file is listed
first. ``drift-doctor audit`` reads these events back and re-verifies
the latest one per model, kind, and object.

The fold: how state is derived
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
