Getting started
===============

In this tutorial you take the example fleet that ships with the tool,
capture a baseline, watch the detector report seventeen seeded
findings, seed one more by hand, and cascade the fixes back. It takes
about ten minutes, and every output below was produced by
``drift-doctor`` 1.2.1 on that fleet.

Prerequisites
----------------

- Python 3.10 or later. Check with ``python --version`` (``python3
  --version`` on macOS and Linux); the tool refuses to install on an
  older Python.
- Git, to fetch the example fleet.
- Optionally, Power BI Desktop (Windows only) if you want to open the
  models and see the drift visually; the examples README in the tool
  repository explains how.

0. Install the tool
----------------------

Clone release 1.2.1, create a virtual environment inside it, and
install the package into it.

::

    # bash / macOS / Linux
    git clone --branch v1.2.1 https://github.com/C-Kapsalis/tmdl-drift-doctor.git
    cd tmdl-drift-doctor
    python3 -m venv .venv
    . .venv/bin/activate
    pip install .
    drift-doctor --version

::

    # PowerShell / Windows
    git clone --branch v1.2.1 https://github.com/C-Kapsalis/tmdl-drift-doctor.git
    Set-Location tmdl-drift-doctor
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install .
    drift-doctor --version

The last command prints the version you installed:

::

    drift-doctor, version 1.2.1

1. Lay out the fleet
------------------------

Running the tool writes state and fixes models in place, so copy the
example fleet somewhere writable and keep the shipped one pristine:

::

    # bash / macOS / Linux
    cp -r examples/fleet /tmp/gym-fleet
    cd /tmp/gym-fleet

::

    # PowerShell / Windows
    Copy-Item -Recurse examples\fleet $env:TEMP\gym-fleet
    Set-Location $env:TEMP\gym-fleet

From here on, a ``drift-doctor`` command is typed the same way in both
shells. Where a step needs a shell feature (a redirect, a filter), both
forms are shown.

The layout is one template model and two derived ("franchise") models,
each wrapped as a Power BI Desktop project (``GymChain.pbip``):

::

    fleet.yml
    template/GymChain.pbip
    template/GymChain.SemanticModel/definition/...
    derived/alpha/GymChain.pbip
    derived/alpha/GymChain.SemanticModel/definition/...
    derived/bravo/GymChain.pbip
    derived/bravo/GymChain.SemanticModel/definition/...

``fleet.yml`` names the template, the derived models, the mapping
tables, and the allowlist of drift kinds that may be fixed. The
example's allowlist permits every non-destructive kind the fleet needs
and lists one deletion kind, ``retire.measure``, which still needs
``--sync`` at run time. Its active lines, without the comments, are:

::

    version: 1
    template: template/GymChain.SemanticModel
    models:
      alpha: derived/alpha/GymChain.SemanticModel
      bravo: derived/bravo/GymChain.SemanticModel
    mapping_tables:
      - Plan Map
    state_dir: .drift-doctor
    allowlist:
      kinds:
        - table.missing
        - column.missing
        - column.property_drift
        - measure.missing
        - measure.expression_drift
        - measure.property_drift
        - measure.wrong_host
        - expression.drift
        - mapping_row.missing
        - relationship.missing
        - relationship.modified
        - retire.measure
      expressions:
        - Reporting Start Date
        - Portal URL

2. Capture the baseline
---------------------------

::

    $ drift-doctor capture
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=17 measures=9 relationships=3 mapping_rows=4 expressions=3

The first line prints the absolute path of your copy. The baseline is
the committed statement of what the template contains. Every
``detect`` and ``remediate`` run compares the derived models against
it, and refuses to run (exit 2) if the template has changed since the
last capture.

3. Detect the seeded drift
-------------------------------

The example franchises ship with drift already seeded:

::

    $ drift-doctor detect

    ── alpha: 8 finding(s)
      measure.missing              Members[New Members #]
      measure.expression_drift     Visits[Total Visits]
          template: COUNTROWS(Visits)
          derived:  COUNTROWS(FILTER(Visits, Visits[DurationMinutes] > 0))
      measure.property_drift       Visits[Avg Visit Duration]
          template: formatString=0.0
          derived:  formatString=0.00
      measure.wrong_host           Visits[Visits per Member]
          template: Visits
          derived:  Members
      expression.drift             Portal URL
          template: expression 'Portal URL' = "https://portal.gymchain.example/reports" meta [IsParameterQuery = true, IsParameterQueryRequ…
          derived:  expression 'Portal URL' = "https://portal.gymchain.example/legacy-reports" meta [IsParameterQuery = true, IsParameterQu…
      expression.drift             Reporting Start Date
          template: expression 'Reporting Start Date' = #date(2024, 1, 1) meta [IsParameterQuery = true, IsParameterQueryRequired = true, T…
          derived:  expression 'Reporting Start Date' = #date(2023, 6, 1) meta [IsParameterQuery = true, IsParameterQueryRequired = true, T…
      extra.measure                Classes[Alpha Seats Left]  [advisory]
      extra.measure                Members[Alpha Loyalty Score]  [advisory]

    ── bravo: 9 finding(s)
      table.missing                Classes
      column.property_drift        Members[JoinDate]
          template: dataType=dateTime, formatString=yyyy-mm-dd, sourceColumn=JoinDate, summarizeBy=none
          derived:  dataType=dateTime, formatString=dd/mm/yyyy, sourceColumn=JoinDate, summarizeBy=none
      column.missing               Members[MembershipTier]
      mapping_row.missing          Plan Map/elite
          template: {"elite", "Elite", 89}
          derived:  None
      relationship.missing         Members[MembershipTier] -> Plan Map[PlanKey]
          template: (engine defaults)
          derived:  None
      relationship.modified        Visits[MemberId] -> Members[MemberId]
          template: (engine defaults)
          derived:  crossFilteringBehavior=bothDirections
      relationship.extra           Members[JoinDate] -> Promotions[StartDate]  [advisory]
      model.count_below_template   measures  [not allowlisted]
          template: 9
          derived:  8
      model.count_below_template   dax_expressions  [not allowlisted]
          template: 9
          derived:  8

    ── summary: actionable=14 advisory=3 overridden=0 errors=0

    [GAP ] alpha
        fact_tables=4 f_measures=0 user_facing=9 helpers=1
        - missing: New Members #, Visits per Member
    [GAP ] bravo
        fact_tables=3 f_measures=0 user_facing=7 helpers=1
        - missing: Classes
    Summary: 0/2 models in cascade

``detect`` exits 1, meaning actionable drift exists, which is what
makes it a CI gate. Read the report in this order:

- The ``[advisory]`` findings are the franchises' own work: alpha's
  ``Alpha Loyalty Score`` and ``Alpha Seats Left``, and bravo's own
  relationship. The tool reports them and never deletes them unless a
  person answers yes on a terminal.
- The two ``model.count_below_template`` findings say that bravo holds
  fewer measures and fewer DAX expressions than the template (it lacks
  the ``Classes`` table and its measure). The kind is not in the
  allowlist, so it prints ``[not allowlisted]``, and it has no automated
  fix, but it still counts as actionable: a count floor fails the gate
  whatever the allowlist says. It clears when the missing table is
  copied in.
- ``measure.wrong_host``: alpha keeps ``Visits per Member`` on
  ``Members``. Measure names are model-global, so it is not reported as
  missing from ``Visits``; the fix moves the block instead of inserting
  a second copy.
- Relationships are matched on their columns, not their names or
  GUIDs, so alpha's relationships (same columns, different block names)
  are not drift.
- ``Portal URL`` differs only inside an ``https://`` string, and it is
  caught. A shared expression is compared as it is written, comments
  included, so a changed comment is drift on its own. Bravo re-saved
  ``Reporting Start Date`` with its ``meta [...]`` bag in a different
  order, and that is not flagged, because the bag is put in canonical
  order before comparing.
- The ``Data Source`` parameter differs in both franchises and is not
  flagged, because only the shared expressions named under
  ``allowlist.expressions`` are compared for content. Cascading a
  connection parameter would point every tenant at the template's
  warehouse.
- The closing block is the cascade report: one ``[GAP ]`` or ``[OK  ]``
  block per model, with the shape of the model (fact tables, filter
  measures, user-facing measures, helpers) and what it is missing, then
  how many models are in cascade.

4. Seed one more drift yourself
-------------------------------------

Open ``derived/bravo/GymChain.SemanticModel/definition/tables/Visits.tmdl``
and change the ``Total Visits`` DAX, for example to
``COUNTROWS(Visits) + 1``. Run ``drift-doctor detect`` again: bravo now
has ten findings, and the new one is:

::

      measure.expression_drift     Visits[Total Visits]
          template: COUNTROWS(Visits)
          derived:  COUNTROWS(Visits) + 1

Undo the edit before you continue, so that the transcripts below match
your screen line by line.

5. Preview the fix
---------------------

Always preview first. ``--dry-run`` prints a unified diff for every
fix and writes nothing, not even the ledger:

::

    $ drift-doctor remediate --dry-run
    [would apply] bravo: table.missing Classes — copy table from template + register in model.tmdl (review the partition source — it is the template's) [asked; batch-safe under --yes]
    --- a//tmp/gym-fleet/derived/bravo/GymChain.SemanticModel/definition/tables/Classes.tmdl
    +++ b//tmp/gym-fleet/derived/bravo/GymChain.SemanticModel/definition/tables/Classes.tmdl
    @@ -0,0 +1,35 @@
    +table Classes
    +	lineageTag: 92d8ee52-125c-40e7-b70f-5f86a355c987
    ...
    [would apply] bravo: column.missing Members[MembershipTier] — insert column block from template (fresh lineage tag) [asked; batch-safe under --yes]
    ...
    [skipped] alpha: extra.measure Classes[Alpha Seats Left] — advisory — this object exists only in the derived model; extensions are reported for review, never auto-remediated. Edit the derived model directly if it is unwanted.
    [skipped] alpha: extra.measure Members[Alpha Loyalty Score] — advisory — this object exists only in the derived model; extensions are reported for review, never auto-remediated. Edit the derived model directly if it is unwanted.
    [skipped] bravo: relationship.extra Members[JoinDate] -> Promotions[StartDate] — advisory — this object exists only in the derived model; extensions are reported for review, never auto-remediated. Edit the derived model directly if it is unwanted.
    [manual] bravo: model.count_below_template measures — kind 'model.count_below_template' has no automated fix — resolve it by editing the model directly
    [manual] bravo: model.count_below_template dax_expressions — kind 'model.count_below_template' has no automated fix — resolve it by editing the model directly

    ── summary: applied=0 would-apply=12 skipped=3 manual=2 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0

    ── Sync summary (DRY-RUN):
    alpha: applied=6 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0
    bravo: applied=6 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0
    FLEET TOTAL: applied=12 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0

(``...`` marks lines left out of this page. The lineage tags in your
diff differ: a copied block always gets a fresh one.)

Fixes run in dependency order (tables, columns, expressions, mapping
rows, measures, relationships), so bravo's missing relationship, which
needs the missing ``MembershipTier`` column, is planned after that
column. The tag at the end of each ``[would apply]`` line says how a
real run treats the fix: ``[asked; batch-safe under --yes]`` means a
terminal run asks for it and a ``--yes`` run may apply it without
asking; ``[asked]`` means only a person can approve it;
``[destructive: asked, never under --yes]`` marks a deletion.

6. See what a script would do
--------------------------------

``remediate`` confirms every fix with a question, and a question needs
a terminal. A script, a pipe, a CI job and an IDE agent have no
terminal, so for them the questions are disabled and every item is
treated as a "no". You can see this without changing anything: run
``remediate`` with its input taken from an empty source.

::

    # bash / macOS / Linux
    drift-doctor remediate < /dev/null

::

    # PowerShell / Windows
    $null | drift-doctor remediate

The run says so once, and the models and the ledger are left alone:

::

    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [skipped] bravo: table.missing Classes — non-interactive: not applied without --yes
    [skipped] bravo: column.missing Members[MembershipTier] — non-interactive: not applied without --yes
    ...
    [precondition] bravo: relationship.missing Members[MembershipTier] -> Plan Map[PlanKey] — relationship endpoint(s) not in the model and not being added in this run: Members[MembershipTier]
    ...
    ── summary: applied=0 would-apply=0 skipped=14 manual=2 blocked=0 auto_skipped_precondition=1 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=11 failed=0

A script that does mean to write names the kinds and passes ``--yes``
(for example ``drift-doctor remediate --yes --kind measure.missing``),
and even then gets only the kinds that are safe without a person and
never a deletion. ``--yes`` on its own is refused with exit 2, so a
script can never apply every kind by accident:

::

    $ drift-doctor remediate --yes
    ERROR: --yes requires an explicit --kind (it never applies every kind at once)

:doc:`../how-to/manage-a-fleet` shows the script forms at work.

7. Apply the fixes
---------------------

**Run this step in an interactive terminal window**, not through a
script, a pipe or an IDE agent. Answer ``y`` to the first
twelve questions. The last three offer to delete the franchises' own
work; answer ``n`` to each:

::

    $ drift-doctor remediate
    [1/17] bravo: table.missing Classes — copy table from template + register in model.tmdl (review the partition source — it is the template's). Apply? [y/n/a/q] y
    [2/17] bravo: column.missing Members[MembershipTier] — insert column block from template (fresh lineage tag). Apply? [y/n/a/q] y
    ...
    [12/17] bravo: relationship.modified Visits[MemberId] -> Members[MemberId] — overwrite relationship properties from template (block name kept). Apply? [y/n/a/q] y
    [13/17] alpha: extra.measure Classes[Alpha Seats Left] — delete the model-only measure from the model. Apply? [y/n/a/q] n
    [14/17] alpha: extra.measure Members[Alpha Loyalty Score] — delete the model-only measure from the model. Apply? [y/n/a/q] n
    [15/17] bravo: relationship.extra Members[JoinDate] -> Promotions[StartDate] — delete the model-only relationship. Apply? [y/n/a/q] n
    [applied] bravo: table.missing Classes — copy table from template + register in model.tmdl (review the partition source — it is the template's)
    [applied] bravo: column.missing Members[MembershipTier] — insert column block from template (fresh lineage tag)
    [applied] bravo: column.property_drift Members[JoinDate] — overwrite column block from template (lineage tag preserved)
    [applied] alpha: expression.drift Portal URL — cascade shared expression 'Portal URL' from template (allowlist-named; lineage tag kept; everything else untouched)
    [applied] alpha: expression.drift Reporting Start Date — cascade shared expression 'Reporting Start Date' from template (allowlist-named; lineage tag kept; everything else untouched)
    [applied] bravo: mapping_row.missing Plan Map/elite — add mapping row 'elite' from template
    [applied] alpha: measure.missing Members[New Members #] — insert measure block from template (fresh lineage tag)
    [applied] alpha: measure.wrong_host Visits[Visits per Member] — move measure block verbatim from 'Members' to the template's host 'Visits' (DAX and lineage tag untouched)
    [applied] alpha: measure.expression_drift Visits[Total Visits] — overwrite measure block from template (lineage tag preserved)
    [applied] alpha: measure.property_drift Visits[Avg Visit Duration] — overwrite measure block from template (lineage tag preserved)
    [applied] bravo: relationship.missing Members[MembershipTier] -> Plan Map[PlanKey] — append relationship block from template
    [applied] bravo: relationship.modified Visits[MemberId] -> Members[MemberId] — overwrite relationship properties from template (block name kept)
    [skipped] alpha: extra.measure Classes[Alpha Seats Left] — declined
    [skipped] alpha: extra.measure Members[Alpha Loyalty Score] — declined
    [skipped] bravo: relationship.extra Members[JoinDate] -> Promotions[StartDate] — declined
    [manual] bravo: model.count_below_template measures — kind 'model.count_below_template' has no automated fix — resolve it by editing the model directly
    [manual] bravo: model.count_below_template dax_expressions — kind 'model.count_below_template' has no automated fix — resolve it by editing the model directly

    ── summary: applied=12 would-apply=0 skipped=3 manual=2 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0

    ── Sync summary (APPLIED):
    alpha: applied=6 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0
    bravo: applied=6 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0
    FLEET TOTAL: applied=12 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0

The run asks fifteen questions; the position counts all seventeen
items, including the two ``[manual]`` count floors that are never
asked. At a question, ``a`` answers yes to the rest of the
non-destructive questions and ``q`` stops the run.

Now check the result. ``detect`` exits 0, with only the three
advisories left, and both models are in cascade (the count floors
cleared when bravo got its ``Classes`` table):

::

    $ drift-doctor detect

    ── alpha: 2 finding(s)
      extra.measure                Classes[Alpha Seats Left]  [advisory]
      extra.measure                Members[Alpha Loyalty Score]  [advisory]

    ── bravo: 1 finding(s)
      relationship.extra           Members[JoinDate] -> Promotions[StartDate]  [advisory]

    ── summary: actionable=0 advisory=3 overridden=0 errors=0

    [OK  ] alpha
        fact_tables=4 f_measures=0 user_facing=10 helpers=1
    [OK  ] bravo
        fact_tables=4 f_measures=0 user_facing=8 helpers=1
    Summary: 2/2 models in cascade

Run ``drift-doctor remediate`` a second time and answer ``n`` to the
three deletion offers: the summary says ``applied=0``, because every
fix is idempotent.

If bravo's day-first ``JoinDate`` format had been deliberate, the right
move would have been an ``expression`` override on bravo's entry in
``fleet.yml`` (with a reason) instead of a cascade; the finding then
prints as an ACK and never fails ``detect``. See
:doc:`../how-to/manage-a-fleet`.

8. Inspect the audit trail
-----------------------------

Every applied fix left a line
in the append-only ledger:

::

    $ drift-doctor ledger
    2026-10-22T16:26:19+00:00  remediated  table.missing  model=bravo  Classes  — copy table from template + register in model.tmdl (review the partition source — it is the template's)
    2026-10-22T16:26:19+00:00  remediated  column.missing  model=bravo  Members[MembershipTier]  — insert column block from template (fresh lineage tag)
    2026-10-22T16:26:19+00:00  remediated  column.property_drift  model=bravo  Members[JoinDate]  — overwrite column block from template (lineage tag preserved)
    2026-10-22T16:26:19+00:00  remediated  expression.drift  model=alpha  Portal URL  — cascade shared expression 'Portal URL' from template (allowlist-named; lineage tag kept; everything else untouched)
    2026-10-22T16:26:19+00:00  remediated  expression.drift  model=alpha  Reporting Start Date  — cascade shared expression 'Reporting Start Date' from template (allowlist-named; lineage tag kept; everything else untouched)
    2026-10-22T16:26:19+00:00  remediated  mapping_row.missing  model=bravo  Plan Map/elite  — add mapping row 'elite' from template
    2026-10-22T16:26:19+00:00  remediated  measure.missing  model=alpha  Members[New Members #]  — insert measure block from template (fresh lineage tag)
    2026-10-22T16:26:19+00:00  remediated  measure.wrong_host  model=alpha  Visits[Visits per Member]  — move measure block verbatim from 'Members' to the template's host 'Visits' (DAX and lineage tag untouched)
    2026-10-22T16:26:20+00:00  remediated  measure.expression_drift  model=alpha  Visits[Total Visits]  — overwrite measure block from template (lineage tag preserved)
    2026-10-22T16:26:20+00:00  remediated  measure.property_drift  model=alpha  Visits[Avg Visit Duration]  — overwrite measure block from template (lineage tag preserved)
    2026-10-22T16:26:20+00:00  remediated  relationship.missing  model=bravo  Members[MembershipTier] -> Plan Map[PlanKey]  — append relationship block from template
    2026-10-22T16:26:21+00:00  remediated  relationship.modified  model=bravo  Visits[MemberId] -> Members[MemberId]  — overwrite relationship properties from template (block name kept)

``drift-doctor audit`` reads these lines back and confirms that each
added or moved object is still in place (overwrite fixes are left to
``detect``). It exits 4 if one was undone:

::

    $ drift-doctor audit
    ── audit: checked=6 ok=6 reverted=0 superseded=0 error=0

You have captured a baseline, read a drift report, previewed and
applied a cascade, and checked its audit trail.

Where to go next
--------------------

- :doc:`../how-to/manage-a-fleet`: onboard a model, cascade a
  retirement, and recover from an unwanted removal, step by step.
- :doc:`../how-to/run-in-ci`: make drift a build signal with the
  ratchet, the audit and the review queue.
- :doc:`../reference/drift-kinds-and-ledger`: every kind, what triggers
  it and what its fix does.
- The examples README in the tool repository
  (``examples/README.md``) adds a retirement and revival on the same
  fleet, and a loop for opening the models in Power BI Desktop before
  and after remediation.
