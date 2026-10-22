Getting started
===============

In this tutorial you will take the example fleet that ships with the
repository, capture a baseline, watch the detector find seventeen seeded
findings, seed one more by hand, and cascade the fixes back. It takes
about ten minutes.

Prerequisites
----------------

- Python 3.10 or later (the CLI runs on Windows, macOS, and Linux
  alike).
- Nothing else: the repository ships a runnable example fleet under
  ``examples/fleet/`` (a fictional gym chain), and this tutorial uses
  it.
- Optionally, Power BI Desktop (Windows only) if you want to open the
  models and see the drift visually; see the examples README's guide to
  opening the models in Power BI Desktop.

Clone the repository, then install the package from inside it (the
commands are identical in every shell):

::

    $ git clone https://github.com/c-kapsalis/tmdl-drift-doctor.git
    $ cd tmdl-drift-doctor
    $ pip install .
    $ drift-doctor --version
    drift-doctor, version 1.2.0

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

Every ``drift-doctor`` command below is byte-identical in both shells;
only the copy step above differs.

The layout is one template model and two derived ("franchise") models,
each wrapped as a Power BI Desktop project (``GymChain.pbip``) you can
open directly:

::

    fleet.yml
    template/GymChain.pbip                       # open in Power BI Desktop
    template/GymChain.SemanticModel/definition/...
    derived/alpha/GymChain.pbip
    derived/alpha/GymChain.SemanticModel/definition/...
    derived/bravo/GymChain.pbip
    derived/bravo/GymChain.SemanticModel/definition/...

``fleet.yml`` names the template, the derived models, the mapping
tables, and, crucially, the allowlist of drift kinds that may be
auto-fixed. The example's starter allowlist permits every
non-destructive kind and lists ``retire.measure``, which still needs
``--sync`` at run time; deletions are double-gated:

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
        - measure.missing
        - measure.expression_drift
        # ... every non-destructive kind, plus retire.measure
      expressions:
        - Reporting Start Date
        - Portal URL

2. Capture the baseline
---------------------------

::

    $ drift-doctor capture
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=17 measures=9 relationships=3 mapping_rows=4 expressions=3

The baseline is the committed statement of what the template contains.
Every ``detect`` and ``remediate`` run compares derived models against
it, and refuses to run if the template has changed since (see
:doc:`../reference/cli-and-configuration`). The path in the first line
is absolute.

3. Detect the seeded drift
-------------------------------

The example franchises ship with drift already seeded, so:

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

``detect`` exited 1, meaning actionable drift exists, which is what
makes it a CI gate. A few more things to notice:

- The ``[advisory]`` findings are the franchises' own work: alpha's
  ``Alpha Loyalty Score`` and ``Alpha Seats Left``, and bravo's own
  relationship. The suite reports them and will never delete them
  without asking (see
  :doc:`../reference/drift-kinds-and-ledger`).
- The two ``model.count_below_template`` findings say that bravo holds
  fewer measures and fewer DAX expressions than the template does. They
  print ``[not allowlisted]`` because the kind has no automated fix at
  all; a model that lost a whole measure is a count floor, not backlog.
- The closing ``[GAP ]`` block is the cascade report: one line per
  model with the shape of the model (fact tables, filter measures,
  user-facing measures, helpers) and what is missing, then the fleet
  total. ``[OK  ]`` replaces ``[GAP ]`` when a model is in cascade.
- ``measure.wrong_host``: alpha keeps ``Visits per Member`` on
  ``Members``. Measure names are model-global, so it is not reported as
  missing from ``Visits``; the fix moves the block instead of inserting
  a second copy.
- Relationships are matched on their columns, not their GUIDs, so
  alpha's relationships (same columns, different block names) are not
  drift.
- ``Portal URL`` differs only inside an ``https://`` string, and it is
  caught. A shared expression is compared as it is written, comments
  and all, so a changed comment is drift on its own; bravo re-saved
  ``Reporting Start Date`` with its ``meta [...]`` bag in a different
  order, and that is not flagged, because the bag is canonicalized.
- The ``Data Source`` parameter also differs in both franchises, and is
  not flagged, because only allowlist-named shared expressions are
  compared for content. Cascading connection parameters would repoint
  every tenant's warehouse.

4. Seed one more drift yourself
-------------------------------------

Open ``derived/bravo/GymChain.SemanticModel/definition/tables/Visits.tmdl``
and change the ``Total Visits`` DAX to anything else. Run
``drift-doctor detect`` again: a new ``measure.expression_drift``
appears for bravo. Undo it, or carry it through the next step; either
works. The transcripts below are from the un-seeded state, so you can
follow them line by line.

5. Preview the fix, then apply it
---------------------------------------

Always preview first. ``--dry-run`` renders unified diffs and writes
nothing, not even the ledger:

::

    $ drift-doctor remediate --dry-run
    [would apply] bravo: table.missing Classes — copy table from template + register in model.tmdl (review the partition source — it is the template's) [asked; batch-safe under --yes]
    --- a/.../derived/bravo/GymChain.SemanticModel/definition/tables/Classes.tmdl
    +++ b/.../derived/bravo/GymChain.SemanticModel/definition/tables/Classes.tmdl
    @@ -0,0 +1,35 @@
    +table Classes
    +	lineageTag: 33347573-7252-425c-a415-d44aed4a1271
    ...
    [would apply] bravo: column.missing Members[MembershipTier] — insert column block from template (fresh lineage tag) [asked; batch-safe under --yes]
    ...
    ── summary: applied=0 would-apply=12 skipped=3 manual=2 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0

    ── Sync summary (DRY-RUN):
    alpha: applied=6 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0
    bravo: applied=6 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0
    FLEET TOTAL: applied=12 skipped_destructive=0 skipped_override=0 skipped_divergent=0 auto_skipped_precondition=0 failed=0

Fixes run in dependency order (tables, columns, expressions, mapping
rows, measures, relationships), so bravo's missing relationship, which
needs the missing ``MembershipTier`` column, is planned after that
column. The trailing tag on each line says how the run would treat the
fix: ``[asked; batch-safe under --yes]`` means the run would ask for it
on a terminal and a ``--yes`` run would apply it without asking;
``[destructive: asked, never under --yes]`` marks a deletion.

Now apply. **Which form you get depends on whether you have a
terminal**, because ``remediate`` confirms every fix with a question
and a question needs a terminal. The two runs below start from the same
state: use the one that matches where you are running.

**On a terminal, apply the fixes like this.** ``remediate`` asks
before every fix (``y``/``n``, ``a`` = yes to the rest, ``q`` = stop),
and it offers to delete a model's own extras, so answer those with
``n`` unless you really mean it:

::

    $ drift-doctor remediate
    [1/17] bravo: table.missing Classes — copy table from template + register in model.tmdl (review the partition source — it is the template's). Apply? [y/n/a/q] y
    [2/17] bravo: column.missing Members[MembershipTier] — insert column block from template (fresh lineage tag). Apply? [y/n/a/q] y
    ...
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

**Without a terminal, nothing is applied.** A script, a pipe, a CI job
and an IDE agent all have a stdin that is not a terminal, and then the
questions are disabled and every item is treated as a "no". The run
says so once, and the models and the ledger are left alone:

::

    $ drift-doctor remediate < /dev/null
    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [skipped] bravo: table.missing Classes — non-interactive: not applied without --yes
    [skipped] bravo: column.missing Members[MembershipTier] — non-interactive: not applied without --yes
    ...
    ── summary: applied=0 would-apply=0 skipped=14 manual=2 blocked=0 auto_skipped_precondition=1 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=11 failed=0

To apply from a script, name the kinds you mean and pass ``--yes``:

::

    $ drift-doctor remediate --yes --kind measure.missing
    [applied] alpha: measure.missing Members[New Members #] — insert measure block from template (fresh lineage tag)

    ── summary: applied=1 would-apply=0 skipped=0 manual=0 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0

``--yes`` alone is a usage error, and it never deletes anything: a
deletion needs an interactive yes, or ``--sync`` together with
``--confirm-deletions``:

::

    $ drift-doctor remediate --yes
    ERROR: --yes requires an explicit --kind (it never applies every kind at once)

The skipped items in the interactive run were the advisories you
declined. Run ``drift-doctor remediate`` a second time: ``applied=0``,
every applier is idempotent. When one fix only becomes visible after
another lands, ``drift-doctor remediate --converge`` re-detects and
re-applies until nothing changes. And ``drift-doctor detect`` now exits
0, with only the advisories left:

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

If bravo's day-first ``JoinDate`` format had been deliberate, the right
move would have been an ``expression`` override on bravo's model entry
in ``fleet.yml`` (with a reason) instead of a cascade; the finding then
prints as an ACK and never fails ``detect`` (see
:doc:`../reference/cli-and-configuration`).

6. Inspect the audit trail
-------------------------------

Every applied fix left a line in the append-only ledger:

::

    $ drift-doctor ledger
    2026-10-12T09:14:48+00:00  remediated  table.missing  model=bravo  Classes  — copy table from template + register in model.tmdl (review the partition source — it is the template's)
    2026-10-12T09:14:48+00:00  remediated  column.missing  model=bravo  Members[MembershipTier]  — insert column block from template (fresh lineage tag)
    2026-10-12T09:14:48+00:00  remediated  column.property_drift  model=bravo  Members[JoinDate]  — overwrite column block from template (lineage tag preserved)
    2026-10-12T09:14:48+00:00  remediated  expression.drift  model=alpha  Portal URL  — cascade shared expression 'Portal URL' from template (allowlist-named; lineage tag kept; everything else untouched)
    2026-10-12T09:14:48+00:00  remediated  expression.drift  model=alpha  Reporting Start Date  — cascade shared expression 'Reporting Start Date' from template (allowlist-named; lineage tag kept; everything else untouched)
    2026-10-12T09:14:48+00:00  remediated  mapping_row.missing  model=bravo  Plan Map/elite  — add mapping row 'elite' from template
    2026-10-12T09:14:48+00:00  remediated  measure.missing  model=alpha  Members[New Members #]  — insert measure block from template (fresh lineage tag)
    2026-10-12T09:14:48+00:00  remediated  measure.wrong_host  model=alpha  Visits[Visits per Member]  — move measure block verbatim from 'Members' to the template's host 'Visits' (DAX and lineage tag untouched)
    2026-10-12T09:14:48+00:00  remediated  measure.expression_drift  model=alpha  Visits[Total Visits]  — overwrite measure block from template (lineage tag preserved)
    2026-10-12T09:14:48+00:00  remediated  measure.property_drift  model=alpha  Visits[Avg Visit Duration]  — overwrite measure block from template (lineage tag preserved)
    2026-10-12T09:14:48+00:00  remediated  relationship.missing  model=bravo  Members[MembershipTier] -> Plan Map[PlanKey]  — append relationship block from template
    2026-10-12T09:14:48+00:00  remediated  relationship.modified  model=bravo  Visits[MemberId] -> Members[MemberId]  — overwrite relationship properties from template (block name kept)

``drift-doctor audit`` reads these lines back and confirms each fix is
still in place; it exits 4 if one was undone.

Where to go next
--------------------

- The examples README covers "act two" of this same fleet: retire a
  measure from the template, cascade the removal with ``--sync``, and
  revive it on one franchise. It also has an open-in-Power-BI-Desktop
  loop so you can watch a drifted measure change before and after
  remediation (Windows plus Power BI Desktop).
- :doc:`../how-to/manage-a-fleet`: onboarding a model, cascading a
  retirement, and recovering from an unwanted removal, step by step.
- :doc:`../how-to/run-in-ci`: make drift a build signal with the
  ratchet, the audit, and the review queue.
- :doc:`../reference/drift-kinds-and-ledger`: every kind, its detection
  rule, and its remediation.
