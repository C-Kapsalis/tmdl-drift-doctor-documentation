CLI and configuration reference
====================================

Every command, flag, exit code, and the full ``fleet.yml`` schema, plus
the design decisions behind ``remediate`` that a reader needs before
trusting it against a real fleet.

Commands
-----------

All commands take ``--fleet PATH`` (default ``fleet.yml``).

``drift-doctor capture``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Snapshot the template into ``<state_dir>/baseline.json`` and maintain
the retirement record.

::

    $ drift-doctor capture [--fleet fleet.yml]

It parses the live template and writes the fresh snapshot as the
baseline. If a previous baseline exists, it diffs the two: objects
present before and absent now become ``retired`` ledger events (kinds:
``table``, ``column``, ``measure``, ``mapping_row``; an object covered
by a larger drop, such as a column of a dropped table, is not
double-recorded); actively-retired objects present again become
``revived`` ledger events. Exit code 0 on success.

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
     - Emit findings as a JSON array (``kind``, ``model``, ``ref``,
       ``template_value``, ``derived_value``, ``detail``, ``advisory``).
   * - ``--model NAME``
     - Only the named derived model.
   * - ``--kind PREFIX``
     - Only findings whose kind starts with the prefix (for example
       ``measure.``, ``retire.``).
   * - ``--allow-stale``
     - Proceed even if the template changed since the last capture.

Exit codes: 0, no remediable findings (advisories alone do not fail); 1,
remediable drift exists; error if the baseline is missing or stale
unless ``--allow-stale`` is set.

``drift-doctor remediate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cascade template truth into the derived models.

::

    $ drift-doctor remediate [--kind PREFIX] [--dry-run] [--sync] [--model NAME] [--allow-stale]

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
   * - ``--model NAME``
     - Only the named derived model.
   * - ``--allow-stale``
     - Proceed on a stale baseline, at the risk of misclassifying
       drift.

Every finding passes three gates before an edit happens: the allowlist
(the kind must be named in ``fleet.yml``), the sync gate (``retire.*``
needs ``--sync``), and the write guards (the new content must be valid
TMDL: tab-indented, balanced fences, no duplicate properties, no
property inside a DAX body). Applied actions are appended to the
ledger. Exit codes: 0 on success, including "nothing to do"; 1 if any
apply failed.

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
       ``"Visits[Peak Hour Visits]"``, ``"Plan Map/legacy-gold"``).
       Requires ``--kind``.
   * - ``--kind KIND``
     - Retirement kind: ``table``, ``column``, ``measure``,
       ``mapping_row``.
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
      alpha: franchises/alpha/GymChain.SemanticModel
      bravo: franchises/bravo/GymChain.SemanticModel

    mapping_tables:                             # optional, tables whose DATATABLE
      - Plan Map                                #   rows are diffed row-by-row

    state_dir: .drift-doctor                    # optional, default .drift-doctor
                                                 #   holds baseline.json + ledger.jsonl

    allowlist:                                  # optional, an EMPTY allowlist means
      kinds: [...]                              #   nothing is ever remediated
      expressions: [...]

Every model path, template included, must contain a ``definition/``
directory; ``load_fleet`` fails loudly otherwise.

``allowlist.kinds``
~~~~~~~~~~~~~~~~~~~~~~~

The drift kinds ``remediate`` may apply. Anything not listed is
detected and reported but never fixed. Valid values:

::

    table.missing            column.missing          column.property_drift
    measure.missing          measure.expression_drift  measure.property_drift
    expression.drift         mapping_row.missing
    retire.table             retire.column           retire.measure
    retire.mapping_row

``extra.measure`` and ``extra.column`` are not valid here; advisories
have no applier by design (see "Why nothing cascades by default",
below). ``retire.*`` kinds are additionally gated behind ``--sync``:
listing them here is necessary but not sufficient. Prefix filtering on
the command line (``--kind measure.``) intersects with this list; the
allowlist is the outer boundary.

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

Both are shared fleet state: detection is only meaningful when
everyone, and CI, reads the same baseline and the same retirement
history.

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
