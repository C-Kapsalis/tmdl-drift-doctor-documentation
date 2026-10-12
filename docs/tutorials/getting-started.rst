Getting started
===============

In this tutorial you will take the example fleet that ships with the
repository, capture a baseline, watch the detector find fifteen seeded
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
    baseline written: .drift-doctor/baseline.json
      tables=5 columns=17 measures=9 relationships=3 mapping_rows=4 expressions=3

The baseline is the committed statement of what the template contains.
Every ``detect`` and ``remediate`` run compares derived models against
it, and refuses to run if the template has changed since (see
:doc:`../reference/cli-and-configuration`).

3. Detect the seeded drift
-------------------------------

The example franchises ship with drift already seeded, so:

::

    $ drift-doctor detect

    -- alpha: 8 finding(s)
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
      expression.drift             Reporting Start Date
      extra.measure                Classes[Alpha Seats Left]  [advisory]
      extra.measure                Members[Alpha Loyalty Score]  [advisory]

    -- bravo: 7 finding(s)
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

    -- summary: actionable=12 advisory=3 overridden=0 errors=0

``detect`` exited 1, meaning actionable drift exists, which is what
makes it a CI gate. A few more things to notice:

- The ``[advisory]`` findings are the franchises' own work: alpha's
  ``Alpha Loyalty Score`` and ``Alpha Seats Left``, and bravo's own
  relationship. The suite reports them and will never delete them (see
  :doc:`../reference/drift-kinds-and-ledger`).
- ``measure.wrong_host``: alpha keeps ``Visits per Member`` on
  ``Members``. Measure names are model-global, so it is not reported as
  missing from ``Visits``; the fix moves the block instead of inserting
  a second copy.
- Relationships are matched on their columns, not their GUIDs, so
  alpha's relationships (same columns, different block names) are not
  drift.
- ``Portal URL`` differs only inside an ``https://`` string, and it is
  caught: comment stripping never touches string literals. Bravo
  re-saved ``Reporting Start Date`` with its ``meta [...]`` bag in a
  different order, and that is not flagged.
- The ``Data Source`` parameter also differs in both franchises, and is
  not flagged, because only allowlist-named shared expressions are
  compared. Cascading connection parameters would repoint every
  tenant's warehouse.

4. Seed one more drift yourself
-------------------------------------

Open ``derived/bravo/GymChain.SemanticModel/definition/tables/Visits.tmdl``
and change the ``Total Visits`` DAX to anything else. Run
``drift-doctor detect`` again: a new ``measure.expression_drift``
appears for bravo. Undo it, or carry it through the next step; either
works.

5. Preview the fix, then apply it
---------------------------------------

Always preview first. ``--dry-run`` renders unified diffs and writes
nothing, not even the ledger:

::

    $ drift-doctor remediate --dry-run
    [would apply] bravo: table.missing Classes - copy table from template + register in model.tmdl (review the partition source - it is the template's)
    --- a/.../derived/bravo/GymChain.SemanticModel/definition/tables/Classes.tmdl
    +++ b/.../derived/bravo/GymChain.SemanticModel/definition/tables/Classes.tmdl
    @@ -0,0 +1,35 @@
    +table Classes
    +	lineageTag: 2a44f7df-2c7c-4e71-8460-1eb988db8282
    ...
    -- summary: applied=0 would-apply=12 skipped=3 blocked=0 auto_skipped_precondition=0 overridden=0 failed=0

Fixes run in dependency order (tables, columns, expressions, mapping
rows, measures, relationships), so bravo's missing relationship, which
needs the missing ``MembershipTier`` column, is planned after that
column. Then apply:

::

    $ drift-doctor remediate
    ...
    [skipped] alpha: extra.measure Members[Alpha Loyalty Score] - advisory - this object exists only in the derived model; extensions are reported for review, never auto-remediated. ...
    -- summary: applied=12 would-apply=0 skipped=3 blocked=0 auto_skipped_precondition=0 overridden=0 failed=0

The skipped items are the advisories. Run ``drift-doctor remediate``
a second time: ``applied=0``, every applier is idempotent. When one fix
only becomes visible after another lands, ``drift-doctor remediate
--converge`` re-detects and re-applies until nothing changes. And
``drift-doctor detect`` now exits 0, with only the advisories left:

::

    $ drift-doctor detect

    -- alpha: 2 finding(s)
      extra.measure                Classes[Alpha Seats Left]  [advisory]
      extra.measure                Members[Alpha Loyalty Score]  [advisory]

    -- bravo: 1 finding(s)
      relationship.extra           Members[JoinDate] -> Promotions[StartDate]  [advisory]

    -- summary: actionable=0 advisory=3 overridden=0 errors=0

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
    2026-10-12T09:14:48+00:00  remediated  table.missing  model=bravo  Classes  - copy table from template + register in model.tmdl (review the partition source - it is the template's)
    2026-10-12T09:14:48+00:00  remediated  column.missing  model=bravo  Members[MembershipTier]  - insert column block from template (fresh lineage tag)
    2026-10-12T09:14:48+00:00  remediated  column.property_drift  model=bravo  Members[JoinDate]  - overwrite column block from template (lineage tag preserved)
    2026-10-12T09:14:48+00:00  remediated  expression.drift  model=alpha  Portal URL  - cascade shared expression 'Portal URL' from template (allowlist-named; everything else untouched)
    2026-10-12T09:14:48+00:00  remediated  expression.drift  model=alpha  Reporting Start Date  - cascade shared expression 'Reporting Start Date' from template (allowlist-named; everything else untouched)
    2026-10-12T09:14:48+00:00  remediated  mapping_row.missing  model=bravo  Plan Map/elite  - add mapping row 'elite' from template
    2026-10-12T09:14:48+00:00  remediated  measure.missing  model=alpha  Members[New Members #]  - insert measure block from template (fresh lineage tag)
    2026-10-12T09:14:48+00:00  remediated  measure.wrong_host  model=alpha  Visits[Visits per Member]  - move measure block verbatim from 'Members' to the template's host 'Visits' (DAX and lineage tag untouched)
    2026-10-12T09:14:48+00:00  remediated  measure.expression_drift  model=alpha  Visits[Total Visits]  - overwrite measure block from template (lineage tag preserved)
    2026-10-12T09:14:48+00:00  remediated  measure.property_drift  model=alpha  Visits[Avg Visit Duration]  - overwrite measure block from template (lineage tag preserved)
    2026-10-12T09:14:48+00:00  remediated  relationship.missing  model=bravo  Members[MembershipTier] -> Plan Map[PlanKey]  - append relationship block from template
    2026-10-12T09:14:48+00:00  remediated  relationship.modified  model=bravo  Visits[MemberId] -> Members[MemberId]  - overwrite relationship properties from template (block name kept)

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
