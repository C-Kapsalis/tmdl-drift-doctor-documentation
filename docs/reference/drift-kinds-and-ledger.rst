Drift kinds and ledger reference
=====================================

Every finding has a dotted ``kind``. This page lists every kind
``drift-doctor`` 1.2.1 can report, the gates each one must pass before
``remediate`` writes it, and, for the core kinds, what triggers it,
what the fix does, and when cascading it is the wrong call. Then the
ledger: the append-only record that makes every retirement and every
applied fix reconstructable later.

Every kind at a glance
---------------------------

The tool reports fifty-eight kinds, plus two families whose last part
is the analysis category (``fieldparam.cross_level.<category>`` and
``fieldparam.plot_specific_extra.<category>``). The columns come from
the 1.2.1 source (``REMEDIABLE_KINDS``, ``ADVISORY_KINDS``,
``SYNC_ONLY_KINDS``, ``RETIREMENT_FINDING_KINDS`` and ``ALWAYS_GATING``
in ``detect.py``; ``BATCH_SAFE_KINDS`` and ``DESTRUCTIVE_PREFIXES`` in
``remediate.py``):

- **Fix**: ``remediate`` has an automated fix. "advisory" means the
  model's own work, never removed without a person; "report" means
  report-only. Every fix also needs the kind in ``allowlist.kinds``.
- **--yes**: a ``--yes --kind`` run may apply it without a person.
- **--sync**: the run must pass ``--sync``.
- **Deletes**: a deletion. It is applied only in a ``--sync`` run,
  with a yes on a terminal or with ``--confirm-deletions``; never under
  ``--yes``.
- **Gates**: "always" means the kind fails ``detect`` whatever
  ``allowlist.kinds`` says.

Any finding can also be acknowledged per model by an override in
``fleet.yml``, which prints it as an ACK and never remediates it (see
:doc:`cli-and-configuration`).

.. list-table::
   :header-rows: 1
   :widths: 40 12 10 10 10 10

   * - Kind
     - Fix
     - --yes
     - --sync
     - Deletes
     - Gates
   * - ``table.missing``
     - yes
     - yes
     -
     -
     -
   * - ``column.missing``
     - yes
     - yes
     -
     -
     -
   * - ``column.property_drift``
     - yes
     - yes
     -
     -
     -
   * - ``measure.missing``
     - yes
     - yes
     -
     -
     -
   * - ``measure.expression_drift``
     - yes
     - yes
     -
     -
     -
   * - ``measure.property_drift``
     - yes
     - yes
     -
     -
     -
   * - ``measure.wrong_host``
     - yes
     - yes
     -
     -
     -
   * - ``measure.duplicate_host``
     - yes
     - yes
     -
     -
     -
   * - ``measure.renamed``
     - yes
     - yes
     -
     -
     -
   * - ``expression.drift``
     - yes
     - yes
     -
     -
     -
   * - ``expression.missing``
     - yes
     - yes
     -
     -
     -
   * - ``mapping_row.missing``
     - yes
     - yes
     -
     -
     -
   * - ``mapping_category.missing``
     - yes
     - yes
     -
     -
     -
   * - ``relationship.missing``
     - yes
     - yes
     -
     -
     -
   * - ``relationship.modified``
     - yes
     - yes
     -
     -
     -
   * - ``relationship.casing_mismatch``
     - yes
     - yes
     -
     -
     -
   * - ``category_annotation.undeclared``
     - yes
     - yes
     -
     -
     -
   * - ``category_annotation.orphaned``
     - report
     -
     -
     -
     -
   * - ``fieldparam.row_missing``
     - yes
     - yes
     -
     -
     -
   * - ``fieldparam.row_drift``
     - yes
     -
     -
     -
     -
   * - ``fieldparam.cross_level.<category>``
     - yes
     - yes
     -
     -
     -
   * - ``fieldparam.plot_specific_extra.<category>``
     - yes
     - yes
     -
     -
     -
   * - ``fieldparam.blank_row``
     - yes
     - yes
     -
     -
     -
   * - ``fieldparam.schema_modernize``
     - yes
     - yes
     -
     -
     -
   * - ``fieldparam.schema_blocked``
     - report
     -
     -
     -
     -
   * - ``fieldparam.dangling_row``
     - yes
     -
     -
     -
     -
   * - ``fieldparam.dangling_selector``
     - yes
     - yes
     -
     -
     -
   * - ``fieldparam.category_missing``
     - report
     -
     -
     -
     -
   * - ``refresh_policy.missing``
     - yes
     -
     -
     -
     -
   * - ``refresh_policy.window_drift``
     - yes
     -
     -
     -
     -
   * - ``refresh_policy.invalid``
     - yes
     -
     -
     -
     -
   * - ``refresh_policy.client_only``
     - report
     -
     -
     -
     -
   * - ``visibility.hidden_user_facing``
     - yes
     -
     -
     -
     -
   * - ``visibility.helper_visible``
     - yes
     -
     -
     -
     -
   * - ``ifilter.coverage_gap``
     - yes
     -
     -
     -
     -
   * - ``ffilter.coverage_gap``
     - yes
     -
     -
     -
     -
   * - ``ffilter.uncategorized``
     - report
     -
     -
     -
     -
   * - ``model.count_below_template``
     - report
     -
     -
     -
     - always
   * - ``extra.measure``
     - advisory
     -
     -
     -
     -
   * - ``extra.column``
     - advisory
     -
     -
     -
     -
   * - ``extra.mapping_row``
     - advisory
     -
     -
     -
     -
   * - ``relationship.extra``
     - advisory
     -
     -
     -
     -
   * - ``retire.table``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.column``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.measure``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.mapping_row``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.mapping_category``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.relationship``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.fieldparam_entry``
     - yes
     -
     - yes
     - yes
     -
   * - ``retire.source_view``
     - yes
     - yes
     - yes
     -
     -
   * - ``retire.ifilter_regen``
     - yes
     -
     - yes
     -
     -
   * - ``retire.stranded_ref``
     - yes
     -
     -
     - yes
     - always
   * - ``purge.fieldparam_entry``
     - yes
     -
     - yes
     - yes
     -
   * - ``purge.measure``
     - yes
     -
     - yes
     - yes
     -
   * - ``purge.column``
     - yes
     -
     - yes
     - yes
     -
   * - ``purge.relationship``
     - yes
     -
     - yes
     - yes
     -
   * - ``purge.zmap_row``
     - yes
     -
     - yes
     - yes
     -
   * - ``purge.table``
     - yes
     -
     - yes
     - yes
     -
   * - ``purge.ifilter_regen``
     - yes
     -
     - yes
     - yes
     -
   * - ``column.purge_listed``
     - yes
     -
     - yes
     - yes
     -

Two combinations are worth knowing. ``retire.source_view`` rewrites a
source view rather than deleting anything, so a scheduled job may
apply it with ``--sync --yes --kind retire.source_view``.
``retire.stranded_ref`` is not in the sync-only set, but it counts as
a deletion, and every deletion of a retired or purged object is applied
only in a ``--sync`` run: with a yes on a terminal, or with
``--confirm-deletions``.

The two ``ifilter`` regenerations and ``ffilter.coverage_gap`` call the
generators in `pbip-model-forge <https://github.com/C-Kapsalis/pbip-model-forge>`_.
Without it installed next to ``drift-doctor``, those checks report
nothing (a run says so on standard error) and those fixes refuse to
run.

Missing objects (template to derived)
-------------------------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Fix
   * - ``table.missing``
     - A baseline table is absent from the model.
     - Copy the template's table file (all lineage tags regenerated),
       register ``ref table`` in ``model.tmdl`` and, for a Power Query
       table, its ``PBI_QueryOrder`` entry. The partition source is the
       template's; review it. A missing axis table (``x-Selector``,
       ``x-Plot Specific``, ``y-Selector``, ``y-Plot Specific``) fails
       ``detect`` whatever the allowlist says.
   * - ``column.missing``
     - A baseline column is absent from a shared table.
     - Splice the template's raw column block (fresh lineage tag).
   * - ``measure.missing``
     - A baseline measure is absent from the whole model.
     - Splice the template's raw measure block, ``///`` description
       included (fresh lineage tag).
   * - ``mapping_row.missing``
     - A baseline mapping-table row is absent.
     - Insert the template's row after the last existing row (a
       ``DATATABLE`` table), or re-encode the table (an encoded table).
   * - ``mapping_category.missing``
     - A whole template category is absent from an encoded mapping
       table.
     - Re-encode with the model's rows first and the template rows
       appended; the write is verified and read back.
   * - ``expression.missing``
     - The template declares a shared expression and the model does
       not, whether or not the name is under
       ``allowlist.expressions``.
     - Append the template's block after the existing ones, in
       alphabetical order, with a fresh lineage tag. A name under
       ``connection_parameters`` is reported with a hint and never
       written.

The detector walks the committed baseline, not the live template, and
matches by name: tables by table name, columns by name within the
same-named table, mapping rows by row key. Measures are matched by name
across the whole model, because the engine requires measure names to be
unique model-wide: a template measure found on another table is
``measure.wrong_host`` (below), never ``measure.missing``, so a name
that already exists anywhere is never inserted a second time.

Do not cascade blindly when:

- ``table.missing``, and data sources differ. The copied partition
  carries the template's source query; if the tenant's warehouse layout
  differs, cascade the table, then fix its partition before deploying.
- ``column.missing``, and the column is source-backed. The model
  validates, but the next refresh fails if the tenant's source cannot
  supply the column. Check the source first.
- ``expression.missing``, and the expression is a connection
  parameter. The tool never writes one: copy the declaration from the
  template and set this model's own value.
- **The removal was deliberate.** A tenant may have removed the object
  on purpose. That is a policy decision, not a bug: record it as an
  ``absent`` override with its reason, so the finding becomes an ACK
  instead of standing debt.

Divergence on shared objects
----------------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Fix
   * - ``measure.expression_drift``
     - The normalized DAX differs (comments, fences and whitespace never
       count).
     - Overwrite the model's block with the template's raw block; the
       model's lineage tag is kept.
   * - ``measure.property_drift``
     - The DAX matches but a compared property differs.
     - The same block overwrite.
   * - ``column.property_drift``
     - A shared column's compared properties differ.
     - The same block overwrite.
   * - ``expression.drift``
     - A shared expression named under ``allowlist.expressions``
       differs.
     - Replace exactly that expression block, keeping each
       declaration's own lineage tag; everything else in
       ``expressions.tmdl`` stays byte for byte.

When a measure's expression and properties both drift, one
``measure.expression_drift`` finding is reported, and the block
overwrite fixes both. The compared properties are ``dataType``,
``formatString``, ``displayFolder``, ``summarizeBy``, ``sourceColumn``,
``sortByColumn`` and ``isHidden``. Lineage tags, annotations and other
tooling metadata are excluded on purpose, so a model re-saved on
another machine does not light up the fleet. Measure names that start
with a prefix listed under ``expression_drift_ignore`` are not compared
at all.

Measure DAX is compared in a **normalized** form, so reformatting,
re-indenting or adding a comment never registers as drift:

- ``//``, ``--`` and ``/* */`` comments are stripped only outside
  string literals and quoted identifiers, so a changed
  ``"https://..."`` literal is real drift, not a comment.
- ``meta [k = v, ...]`` records are put in canonical form: items
  split, trimmed, spaced as ``k = v`` and sorted. Power BI Desktop
  reorders these on save; the order carries no meaning.
- Fence markers and runs of whitespace collapse.

.. important::

   **A shared expression is compared differently from a measure.**
   Since 1.2.0 the comparison form of a shared expression drops only
   the lineage-tag lines and puts the ``meta [...]`` record in canonical
   order; **everything else, doc comments and** ``//`` **comments
   included, is compared as written.** A changed comment is drift on
   its own. A name declared more than once is compared on every
   declaration, and the fix rewrites each differing declaration with
   its own lineage tag kept.

Do not cascade blindly when:

- **The model's version is the correct one.** Much expression drift is
  a fix made in one client that never reached the template. Read the
  diff (``--dry-run``) before cascading; if the model is right, fix the
  template, recapture, and cascade the other direction.
- **The logic is genuinely tenant-specific.** A cascade keeps reverting
  a deliberate difference. Model it properly (a differently named
  tenant measure, or a parameter the template reads), or declare an
  ``expression`` override.
- **A data-type or source disagreement is rooted in the source.** If
  the tenant's warehouse really serves a different type or column name,
  cascading the template's value breaks refresh; fix the source or
  declare the divergence.
- **Visibility is deliberately different per tenant.** If one tenant
  hides a measure for contractual reasons, a cascade keeps showing it
  again. Declare an ``expression`` override, or move the difference
  outside the shared surface.

Measure hosts and renames
-----------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Fix
   * - ``measure.wrong_host``
     - A template measure is absent from its template host table but
       present on one or more other tables of the model. One finding
       per measure, against the alphabetically first of those tables;
       the detail says whether the body matches the template.
     - Move the model's block verbatim to the template's host: DAX,
       properties and lineage tag untouched. The destination is written
       first, so an interruption leaves a detectable duplicate, never a
       lost measure. A body that also differs surfaces as
       ``measure.expression_drift`` on the next detect; ``--converge``
       picks it up in the same run.
   * - ``measure.duplicate_host``
     - The model carries a template measure on the template's host
       and on another table. The engine will not load such a model.
     - Remove the copy on the other table; the copy on the template's
       host stays.
   * - ``measure.renamed``
     - The template renamed a measure: one missing name and one
       model-only name share a core (the name with one leading ``-``,
       ``_``, ``!``, ``#``, ``^`` or letter-and-dash stripped, trimmed,
       lower-cased).
     - Rename the model's declaration, rewrite every DAX reference
       (field-parameter ``NAMEOF`` rows included) and, with
       pbi-plot-styler installed, every report binding below the
       model's folder.

A move waits (precondition) while the template's host table is missing
from the model, while the host already carries the name, or while any
DAX references the measure qualified by its old host
(``'Members'[Visits per Member]``), since the move would leave that
reference dangling. Bare ``[Visits per Member]`` references do not
depend on the host and survive the move.

Do not cascade blindly when:

- ``measure.wrong_host``, and something outside the model names the
  old host. Report visuals and other models that bind the measure
  through ``Members`` lose it after the move. The tool checks DAX
  inside the model, not reports; search them first.
- ``measure.wrong_host``, and the host was chosen on purpose. A
  tenant may keep a measure on another table for its display folder or
  field-list layout. Declare that with an ``expression`` override.
- ``measure.duplicate_host``, and the reports bind the other copy.
  Remove the stale copy by hand and declare the arrangement with an
  override instead.
- ``measure.renamed``, and the two names are not a rename. The
  pairing is a name heuristic. An ambiguous core is never paired, and a
  name an override declares is never paired either.

Relationships
-----------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Fix
   * - ``relationship.missing``
     - A template relationship's signature is absent from the model's
       ``relationships.tmdl``.
     - Append the template's raw block (the file is created if absent).
       The template's block name is kept unless it collides with one in
       the model, then a fresh GUID is used.
   * - ``relationship.modified``
     - The signature exists but compared properties differ.
     - Overwrite the model's block with the template's; the model's
       block name is kept.
   * - ``relationship.casing_mismatch``
     - An endpoint names a table or column that the template spells
       with another casing.
     - Rewrite the endpoint to the template's spelling. Reported once
       per mismatching part, instead of as a missing plus an extra
       relationship.
   * - ``relationship.extra``
     - A model-only relationship between two template tables.
     - None; advisory.

Identity is the field signature ``FromTable[col] -> ToTable[col]``.
Block names, which are usually GUIDs that differ per model and change
when Desktop recreates a relationship, never take part. The compared
properties are ``fromCardinality``, ``toCardinality``, ``isActive``,
``crossFilteringBehavior``, ``securityFilteringBehavior`` and
``relyOnReferentialIntegrity``, each normalized to its engine default
when omitted, so ``isActive: true`` written out equals a block that
leaves it implicit. A relationship touching a model-only table is not a
finding. ``relationship.missing`` waits (precondition) until both
endpoint columns exist in the model or are added earlier in the same
run.

Do not cascade blindly when:

- ``relationship.missing``, and the tenant's data cannot honor it.
  A many-to-one relationship needs unique keys on the one side; if the
  tenant's data has duplicates, or the new relationship creates an
  ambiguous filter path with one of the tenant's own, the model fails
  to refresh or picks a path silently. Check the keys and the existing
  paths first.
- ``relationship.modified``, and the difference is deliberate.
  Bidirectional filtering set for row-level security, or an inactive
  relationship a tenant activated for its own reports, is a decision,
  not drift. Declare it with an ``expression`` override.

Extras (the model's own work), advisory
----------------------------------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
   * - ``extra.measure``
     - A model-only measure on a shared table.
   * - ``extra.column``
     - A model-only column on a shared table (not reported for a name
       under ``ignore_columns``, nor for a declared ``extension``).
   * - ``extra.mapping_row``
     - A model-only row in an encoded mapping table.
   * - ``relationship.extra``
     - A model-only relationship between two shared tables.

The template is a core, not a superset: every derived model must
contain it, but a model may legitimately extend beyond it, so absence
from the template is never by itself evidence that an object is wrong.
An extra might be tenant customization to keep, an experiment, or
debris from a template retirement, and presence alone cannot tell
those apart; only a recorded ``retired`` ledger event can. That is why
``extra.*`` has no fix. Model-only tables, and everything on them, are
not findings at all.

Usually the right response to an advisory is nothing: a stable set of
extras per model is that tenant's custom surface, and ``detect`` exits
0 when only advisories remain. If an extra should become standard, add
it to the template and recapture. If it is debris, delete it by hand,
or answer yes when a terminal run of ``remediate`` offers to delete it
(one question each, naming how many report references would break). A
batch run and a ``--yes`` run never offer.

Retirements (ledger-driven deletions)
-------------------------------------------

Reported only for objects with a ``retired`` ledger event in force
(recorded at recapture, canceled by a revival) that a model still
carries.

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Fix
   * - ``retire.table``
     - A ledger-retired table is still in the model.
     - Delete the table file, remove it from ``model.tmdl`` and from the
       query order, and remove the template-owned or ledger-retired
       relationships touching it.
   * - ``retire.column``
     - A ledger-retired column is still on a shared table.
     - Remove the column block and the template-owned or ledger-retired
       relationships using it.
   * - ``retire.measure``
     - A ledger-retired measure is still in the model. A model measure
       whose core name matches the retired one is retired with it.
     - Remove the measure block.
   * - ``retire.mapping_row``
     - A ledger-retired row is still in a mapping table.
     - Remove exactly that row; sibling rows stay.
   * - ``retire.mapping_category``
     - A ledger-retired category is still in an encoded mapping table.
     - Remove the category's rows. ``blocked`` when the model added
       its own keys to that category.
   * - ``retire.relationship``
     - A ledger-retired relationship (by signature) is still in the
       model. Not reported when an endpoint table or column has its own
       retirement finding, which removes the relationship instead.
     - Remove the relationship block.
   * - ``retire.source_view``
     - The template re-pointed a table to a new source view (the
       ledger's ``source_view_change`` event) and the model still reads
       the old one.
     - Rewrite the view in every spelling (bare or quoted helper call,
       an inline query in the partition and the refresh policy
       together). A model on a view it declares (``source_views``
       override) is retained; a model on some other view needs a
       person. Both go to the run's decision digest.
   * - ``retire.fieldparam_entry``
     - A field-parameter row still points at a measure the template
       retired.
     - Remove exactly those rows; every other row, the row order and
       the table's own formatting stay as they were.
   * - ``retire.ifilter_regen``
     - The ``i-Applied Filters`` measure names an object this run
       removes (a table, a measure or a column), so it would keep a
       stale branch.
     - Regenerate the measure after the removal.
   * - ``retire.stranded_ref``
     - Live DAX still names a table the ledger retired and the model no
       longer declares (comments ignored).
     - Strip a reference that lives inside a dead sensor operand
       (``ISFILTERED('Old Campaigns')`` and similar); a measure that
       reads the retired table for its rows is left to a person. Fails
       a gate whatever the allowlist says.

Additions are provable by presence in the template; removals cannot
work the same way, since "absent from the template" is also exactly
what legitimate tenant customization looks like. The ``retired``
ledger event carves out the one population that may be deleted:
objects provably once in the template, witnessed by the recapture.
Objects inside a bigger drop are not tracked twice: when a whole table
is retired, its measures and columns are covered by the single table
event. A mapping-table row is tracked on its own, since a coarser
retirement could not express "one row leaves, the others stay".

The coupling guard
~~~~~~~~~~~~~~~~~~~~~~

A retirement removes something that provably left the template, but
the model's own work can still depend on it. ``retire.table``,
``retire.column`` and ``retire.measure`` are **blocked** (status
``blocked``, with the reason on the finding and in ``detect`` output)
when any of these depends on the object:

- a model-only measure or calculated column whose DAX references it
  (the scan ignores references inside strings and comments);
- a model-only relationship touching it (template-owned and
  ledger-retired relationships are removed with it instead);
- a column whose ``sortByColumn`` is the retired column;
- a hierarchy level built on the retired column;
- for a table: a measure or column on that table that was not part of
  the table when it left the template (the table's ``retired`` event
  lists its objects), that is, the model's own work.

A name matching ``protected_name_pattern`` is blocked too. A blocked
retirement stays actionable: the model still carries a retired object,
and a person decides. Remove or rewrite the dependent, or keep the
object with a ``retain`` override or a ledger revival.

Template-owned or ledger-retired dependents do not block; their own fix
resolves them. Whether that fix has landed is the retirement's
precondition at apply time: a template measure still reading a retired
column in the model must be overwritten first (earlier in the same
run, which the dependency order arranges when the kind is allowlisted),
or the removal is ``auto_skipped_precondition``.

Do not sync blindly when:

- **Something outside the model still references the object.** The
  guard sees DAX, relationships, sort-by columns and hierarchies inside
  the model. It does not see report visuals bound to a retired measure,
  or tenant data still tagged with a retired mapping-row key. Search
  them first.
- ``retire.relationship``, and a model-only measure activates it.
  ``USERELATIONSHIP`` names the two columns, not the relationship, and
  the guard does not treat it as a dependency. Search the model for
  ``USERELATIONSHIP`` on those columns before syncing.
- **A tenant is contractually still using it.** Revive it for that
  model (``ledger --revive ... --model NAME``) so sync passes leave it
  alone, and keep everyone else on the removal path.
- **The retirement itself was a mistake.** Restore the object in the
  template and recapture; the ledger records a fleet-wide revival.

The 1.2.0 families
----------------------

These kinds come from field-parameter tables, encoded mapping tables,
incremental refresh, measure visibility, the filter measures and the
pristine-category purge. Most fleets that are not built on that
report pattern never see them.

.. list-table::
   :header-rows: 1

   * - Kind
     - Trigger
     - Fix
   * - ``fieldparam.row_missing`` / ``fieldparam.row_drift``
     - A template field-parameter row (matched on its display name) is
       absent or different, and its ``NAMEOF`` resolves in the model.
     - Add or replace the row through the lossless row writer (parked
       rows, comments and group headers survive).
   * - ``fieldparam.cross_level.<category>`` /
       ``fieldparam.plot_specific_extra.<category>``
     - A dimension row is registered at some numbered levels but not
       others, or only in a variant table.
     - Add the row to every numbered level that lacks it (never into a
       narrower level).
   * - ``fieldparam.blank_row``
     - A legend field parameter lacks the template's "no legend" row,
       or it drifted.
     - Append or restore the template's row; an arity mismatch is
       refused.
   * - ``fieldparam.schema_modernize`` / ``fieldparam.schema_blocked``
     - A field-parameter table's columns differ from the template's.
     - Rewrite the column blocks and remap the rows. A table with its
       own extra columns is ``schema_blocked`` and never touched.
   * - ``fieldparam.dangling_row``
     - Live rows whose ``NAMEOF`` points at nothing (the calculated
       table fails to process).
     - Remove exactly those rows.
   * - ``fieldparam.dangling_selector``
     - A selector SWITCH arm calls a measure the model does not have.
     - Remove the arm line.
   * - ``fieldparam.category_missing``
     - The template's field parameters use an analysis category the
       model's mapping table does not carry.
     - None; the mapping table is written by hand.
   * - ``category_annotation.undeclared`` /
       ``category_annotation.orphaned``
     - A model-only mapping category has no ``Category_*`` annotation in
       ``model.tmdl`` / an annotation names no category.
     - Add the annotation (value from git history, else
       ``"<Category> metrics"``) / none.
   * - ``refresh_policy.missing`` / ``refresh_policy.window_drift`` /
       ``refresh_policy.invalid``
     - A fact table lacks the template's incremental-refresh policy /
       its window differs / its policy is malformed.
     - Build the policy from the model's own partition source / rewrite
       the window / copy the partition source into ``sourceExpression``.
       Each records "full refresh owed" in the run's digest.
   * - ``refresh_policy.client_only``
     - The model has a policy the template's table does not.
     - None.
   * - ``visibility.hidden_user_facing`` / ``visibility.helper_visible``
     - A measure with a user-facing name is hidden / a measure with a
       helper name is visible and not on the always-visible list. The
       class is decided by the name alone.
     - Remove the hidden flag / add it.
   * - ``ifilter.coverage_gap``
     - A dimension offered in a y-Selector table is not exposed by the
       ``i-Applied Filters`` measure.
     - Regenerate the measure from the visible dimension set.
   * - ``ffilter.coverage_gap`` / ``ffilter.uncategorized``
     - A fact a user-facing measure reads has no category gate, or a
       category has no gate in ``f-All`` / a fact has no analysis
       category.
     - Add the missing gate measures and lines / none.
   * - ``model.count_below_template``
     - The model holds fewer of a template metric (measures by class,
       fact tables, DAX expressions, ``NAMEOF`` references,
       relationships, axis-family tables) than the template; ``data``
       carries ``metric``, ``client``, ``template``, ``adjustment``,
       ``floor``.
     - None. Fails a gate whatever the allowlist says.
   * - ``purge.*`` / ``column.purge_listed``
     - With ``purge.enabled``: model-only content of an analysis
       category the model never customized / a model-only column on the
       configured purge list.
     - Remove it; protected names, override retentions and data
       extensions are kept, and calls for a person go to the digest.
       Sync runs only.

Preconditions
-----------------

Each fix declares what must already be true in the model when it runs.
They are evaluated at apply time, against the model as earlier fixes in
the same run left it (a dry run tracks what it would have added or
removed):

.. list-table::
   :header-rows: 1

   * - Kind
     - Precondition
   * - ``table.missing``
     - None of the table's template measures already exists elsewhere
       in the model (the copy would duplicate a model-global name).
   * - ``measure.missing``, ``measure.expression_drift``
     - Every table, column and measure the template DAX references
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
Fixes run in dependency order, so most chains complete in one pass.
When a fix only becomes visible after another lands (a moved measure
whose body also differs), ``remediate --converge`` re-detects and
re-applies until nothing changes, at most four passes.

The full order is: ``table.missing``, ``column.missing``,
``column.property_drift``, ``expression.drift``, ``expression.missing``,
``mapping_row.missing``, ``measure.renamed``, ``measure.missing``,
``measure.wrong_host``, ``measure.duplicate_host``,
``measure.expression_drift``, ``measure.property_drift``,
``relationship.missing``, ``relationship.modified``,
``relationship.casing_mismatch``, ``retire.relationship``,
``retire.measure``, ``retire.mapping_row``, ``retire.mapping_category``,
``retire.source_view``, ``retire.column``, ``retire.table``, the purge
block (``purge.fieldparam_entry``, ``purge.measure``, ``purge.column``,
``purge.relationship``, ``purge.zmap_row``, ``purge.table``), then
``retire.fieldparam_entry``, ``purge.ifilter_regen`` and
``retire.ifilter_regen``. The field-parameter and mapping kinds
(``fieldparam.*``, ``mapping_category.missing``,
``category_annotation.undeclared``) follow in their own phase.

Ledger format
-----------------

``<state_dir>/ledger.jsonl`` is one JSON object per line, append-only.
Fleet remediation changes other people's models in bulk, and an
auditable record of it is the minimum standard: "why does tenant alpha
not have the class fill-rate KPI" has to be answerable months later
from the record alone: retired from the template on this date, removed
from alpha by this run, these files touched. Reads fold the stream in
order; nothing is ever rewritten or deleted, so a corrupt line (or a
line that is valid JSON but not an object) makes every read fail
loudly rather than being skipped, or worse, aiming a removal at the
wrong object.

Common fields
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Meaning
   * - ``ts``
     - string
     - UTC ISO-8601 timestamp, added automatically
   * - ``event``
     - string
     - ``retired``, ``revived``, ``remediated`` or ``repointed``
   * - ``kind``
     - string
     - See the per-event sections below
   * - ``ref``
     - string
     - Object reference (formats below)

Reference formats: tables use ``TableName``; columns and measures use
``Table[Object]``; mapping rows use ``Table/row_key`` (or
``Table/category/key`` in an encoded table); mapping categories use
``Table/category``; relationships use their field signature
``From[col] -> To[col]`` (for example
``Visits[PromoId] -> Promotions[PromoId]``).

``retired``
~~~~~~~~~~~~~~

Appended by ``capture`` when an object in the previous baseline is
absent from the fresh snapshot. This is the proof of former template
membership that authorizes a later removal.

::

    {"ts": "2026-10-22T16:32:39+00:00", "event": "retired", "kind": "measure", "ref": "Classes[Class Fill Rate %]", "source": "capture"}

``kind`` is one of ``table``, ``column``, ``measure``, ``mapping_row``,
``mapping_category``, ``relationship``. Mapping-row events also carry
``table`` and ``row_key`` (a mapping-row event without them stops every
read); a mapping-category event carries ``table``, ``category`` and the
``keys`` it held. Table events carry ``objects``, the ``Table[Object]``
refs of the columns and measures the table held when it left the
template; the coupling guard uses it to tell template-era objects from
the model's own work. A relationship is recorded even when its endpoint
table was dropped in the same capture.

``repointed``
~~~~~~~~~~~~~~~~

Appended by ``capture`` once per template table that was re-pointed to
another source view. Its kind is ``source_view_change``, and it is what
authorizes the ``retire.source_view`` cascade.

::

    {"ts": "...", "event": "repointed", "kind": "source_view_change",
     "ref": "Visits:old_view->new_view", "table": "Visits",
     "old_view": "old_view", "new_view": "new_view", "source": "capture"}

``revived``
~~~~~~~~~~~~~~

Cancels a retirement in force without erasing it: the template takes
an object back (recorded fleet-wide at the next capture) or a person
records a deliberate keep with ``ledger --revive``.

::

    {"ts": "2026-10-22T16:33:49+00:00", "event": "revived", "kind": "measure", "ref": "Classes[Class Fill Rate %]", "source": "manual", "model": "alpha", "note": "alpha keeps its class fill-rate KPI"}

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
     - Optional reason

``remediated``
~~~~~~~~~~~~~~~~~~

Appended by ``remediate`` for every applied fix, never in
``--dry-run``.

::

    {"ts": "2026-10-22T16:33:22+00:00", "event": "remediated", "kind": "retire.measure", "model": "alpha", "ref": "Classes[Class Fill Rate %]", "action": "remove retired measure block", "files": ["/tmp/gym-fleet/derived/alpha/GymChain.SemanticModel/definition/tables/Classes.tmdl"]}

Here ``kind`` is the finding kind, ``action`` is the label of what was
done, and ``files`` lists every file the fix touched, as absolute paths
on the machine that ran it. For ``measure.wrong_host`` the ``ref`` is
the template location (``Visits[Visits per Member]``), and the
destination file is listed first. ``drift-doctor audit`` reads these
events back and re-verifies the latest one per model, kind and object.

The fold: how state is derived
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The retirements in force for a model come from walking the stream in
order: ``retired`` puts ``(kind, ref)`` in force; ``revived`` removes
it, for everyone if the event has no ``model``, only for that model if
it does; a later ``retired`` for the same ``(kind, ref)`` puts it back
in force. ``remediated`` events never affect the fold; they are pure
audit. Restoring a wrongly removed object is always the same two
steps: put the block back, then revive the ref (see
:doc:`../how-to/manage-a-fleet`). The mistake and the correction both
stay on the record. Dry runs write neither the models nor the ledger,
so the ledger never claims something that did not happen.
