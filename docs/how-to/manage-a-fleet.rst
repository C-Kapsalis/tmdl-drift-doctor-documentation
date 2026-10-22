Manage a fleet
=================

Three recurring tasks once a fleet is running: bring a new model under
management, cascade a retirement all the way through, and undo a
removal that a client still needed. The transcripts were produced by
``drift-doctor`` 1.2.1 on copies of the example fleet from
:doc:`../tutorials/getting-started`; your timestamps, lineage tags and
paths differ.

.. important::

   **Know which kind of run you are in.** ``remediate`` confirms every
   fix with a question, and a question needs a terminal. On a terminal
   the run asks. Everywhere else (a script, a pipe, a CI job, an IDE
   agent) the questions are disabled, every item is treated as a "no",
   and **nothing is applied**. The run says so once::

       note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.

   So every write in this page has two forms:

   - on a terminal, ``drift-doctor remediate ...`` and answer the
     questions;
   - in a script, ``drift-doctor remediate --yes --kind <kind> ...`` for
     the kinds that are safe without a person, and
     ``drift-doctor remediate --sync --confirm-deletions ...`` for
     deletions.

   ``--yes`` never deletes anything, and ``--confirm-deletions``
   without ``--sync`` is refused (exit 2).

1. Add a model to the fleet
-------------------------------

Goal: bring a new derived model, ``charlie``, under drift management
and work its backlog down to zero.

The model must be a TMDL-format ``*.SemanticModel`` folder with a
``definition/`` directory (``tables/*.tmdl``, ``model.tmdl``, and
optionally ``expressions.tmdl`` and ``relationships.tmdl``). Paths in
``fleet.yml`` are resolved relative to the fleet file. Register the
model under ``models:``:

::

    models:
      alpha: derived/alpha/GymChain.SemanticModel
      bravo: derived/bravo/GymChain.SemanticModel
      charlie: derived/charlie/GymChain.SemanticModel   # new

A path without a ``definition/`` directory fails the next run loudly
instead of skipping the model. ``drift-doctor fleet check`` validates
the file without detecting anything:

::

    $ drift-doctor fleet check
    fleet.yml is valid: 3 model(s).

Adding a model never needs a recapture: the baseline describes the
template, not the fleet.

**Take stock before fixing anything.** Run a scoped, read-only
detection. (In this example, charlie started life as a copy of alpha,
so it carries alpha's drift.)

::

    $ drift-doctor detect --model charlie

    ── charlie: 8 finding(s)
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
          ...
      expression.drift             Reporting Start Date
          ...
      extra.measure                Classes[Alpha Seats Left]  [advisory]
      extra.measure                Members[Alpha Loyalty Score]  [advisory]

    ── summary: actionable=6 advisory=2 overridden=0 errors=0

    [GAP ] charlie
        fact_tables=4 f_measures=0 user_facing=9 helpers=1
        - missing: New Members #, Visits per Member
    Summary: 0/1 models in cascade

An unknown name is a configuration error, not drift, and exits 2:

::

    $ drift-doctor detect --model charly
    Error: unknown model 'charly'; fleet.yml defines: alpha, bravo, charlie

Read the findings before remediating:

- Missing objects are usually safe to cascade.
- Expression and property drift overwrite the model's version. Read the
  diff (``--dry-run``) in case the difference is deliberate.
- Extras (``[advisory]``) are the model's own work. Nothing removes
  them unless a person answers yes on a terminal.

**Record every deliberate difference as an override** instead of
leaving it as standing drift. Switch the entry to the long form; while
the backlog is worked down, ``gating: advisory`` keeps charlie from
failing ``detect`` and the ratchet:

::

    models:
      alpha: derived/alpha/GymChain.SemanticModel
      bravo: derived/bravo/GymChain.SemanticModel
      charlie:
        path: derived/charlie/GymChain.SemanticModel
        gating: advisory            # optional, while onboarding
        overrides:
          - object: Visits[Total Visits]
            kind: expression        # keeps its own definition
            reason: charlie excludes zero-minute visits by contract
            owner: charlie-analytics
            added: 2026-10-22

The override turns the finding into an acknowledgment, and the
advisory gating makes ``detect --model charlie`` exit 0:

::

    $ drift-doctor detect --model charlie

    ── charlie: 7 finding(s)  (gating: advisory)
      measure.missing              Members[New Members #]
      ...
      declared divergence honored (overrides): 1 item(s)
      ACK measure.expression_drift   Visits[Total Visits]  [expression; owner charlie-analytics, added 2026-10-22]
          reason: charlie excludes zero-minute visits by contract

    ── summary: actionable=5 advisory=2 overridden=1 errors=0
    ...

**Cascade one kind at a time.** Preview first:

::

    $ drift-doctor remediate --model charlie --kind measure.missing --dry-run
    [would apply] charlie: measure.missing Members[New Members #] — insert measure block from template (fresh lineage tag) [asked; batch-safe under --yes]
    --- a//tmp/gym-fleet/derived/charlie/GymChain.SemanticModel/definition/tables/Members.tmdl
    +++ b//tmp/gym-fleet/derived/charlie/GymChain.SemanticModel/definition/tables/Members.tmdl
    ...
    ── summary: applied=0 would-apply=1 skipped=0 manual=0 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...

Then apply. On a terminal, answer the question:

::

    $ drift-doctor remediate --model charlie --kind measure.missing
    [1/1] charlie: measure.missing Members[New Members #] — insert measure block from template (fresh lineage tag). Apply? [y/n/a/q] y
    [applied] charlie: measure.missing Members[New Members #] — insert measure block from template (fresh lineage tag)
    ...

In a script, the same command applies nothing; add ``--yes``:

::

    # bash / macOS / Linux
    drift-doctor remediate --model charlie --kind measure.missing < /dev/null      # applies nothing
    drift-doctor remediate --model charlie --kind measure.missing --yes < /dev/null

::

    # PowerShell / Windows
    $null | drift-doctor remediate --model charlie --kind measure.missing          # applies nothing
    $null | drift-doctor remediate --model charlie --kind measure.missing --yes

A ``--kind`` value is a dotted prefix, so ``--kind measure`` takes every
``measure.*`` kind at once, and the override is honored at apply time:

::

    $ drift-doctor remediate --model charlie --kind measure --yes
    [applied] charlie: measure.wrong_host Visits[Visits per Member] — move measure block verbatim from 'Members' to the template's host 'Visits' (DAX and lineage tag untouched)
    [ACK] charlie: measure.expression_drift Visits[Total Visits] — acknowledged by a fleet.yml override (expression): charlie excludes zero-minute visits by contract [owner charlie-analytics, added 2026-10-22]
    [applied] charlie: measure.property_drift Visits[Avg Visit Duration] — overwrite measure block from template (lineage tag preserved)

    ── summary: applied=2 would-apply=0 skipped=0 manual=0 blocked=0 auto_skipped_precondition=0 overridden=1 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...

When one fix only becomes visible after another lands,
``--converge`` re-detects and re-applies until a pass changes nothing
(at most four passes). In a script it still needs ``--yes`` and a
``--kind``:

::

    $ drift-doctor remediate --model charlie --converge --yes --kind expression
    ══ pass 1
    [applied] charlie: expression.drift Portal URL — cascade shared expression 'Portal URL' from template (allowlist-named; lineage tag kept; everything else untouched)
    [applied] charlie: expression.drift Reporting Start Date — cascade shared expression 'Reporting Start Date' from template (allowlist-named; lineage tag kept; everything else untouched)
    ...
    ══ pass 2

    ── summary: applied=0 would-apply=0 skipped=0 manual=0 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...
    ── converged

**Re-gate the model.** Once only advisories and acknowledgments are
left, remove ``gating: advisory`` (``enforced`` is the default). If
the fleet already has a floors file (:doc:`run-in-ci`), the ratchet
fails on a model without a floor:

::

    $ drift-doctor ratchet check
    [RISE] charlie: no floor recorded; record one with `drift-doctor ratchet tighten --allow-new`
    ...
    DRIFT RATCHET RED

Record it, and commit ``floors.json``:

::

    $ drift-doctor ratchet tighten --allow-new
      charlie: recorded at 0
    floors written: /tmp/gym-fleet/.drift-doctor/floors.json

Without ``--allow-new``, ``tighten`` leaves the model out and says
``charlie: no floor (pass --allow-new to record it at 0)``.

Caveats:

- ``table.missing`` copies the template's partition source verbatim.
  If the new model reads a different source, fix the partition after
  the cascade.
- If objects were retired from the template before charlie joined, the
  ledger already lists them, and ``detect`` reports any that charlie
  still carries as ``retire.*``. Remove them with the retirement flow
  in section 2, or keep them with a revival scoped to charlie
  (section 3).

2. Cascade a column retirement
----------------------------------

Goal: a column was removed from the template, and every derived model
that still carries it should drop it too. The flow is the same for
measures, tables, mapping rows and relationships; they are all
retirement kinds. The transcripts start from a fresh copy of the
example fleet with a baseline captured.

**Retire the column in the template.** Edit the template's table file
and delete the column block (the declaration line and its indented
properties and annotations). Remove any template measure that reads it
too, so the template stays self-consistent: here,
``Classes[Capacity]`` and the ``Class Fill Rate %`` measure that
divides by it. Then recapture immediately:

::

    $ drift-doctor capture
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=16 measures=8 relationships=3 mapping_rows=4 expressions=3
      [ledger] retired column: Classes[Capacity]
      [ledger] retired measure: Classes[Class Fill Rate %]

The recapture does two things. The baseline stops listing the column,
so ``detect`` does not report models without it as ``column.missing``
(and the cascade does not copy it back). And the comparison of the old
baseline with the new snapshot proves that the column used to be in
the template, so it appends a ``retired`` event to the ledger. That
proof is what authorizes the removal; absence alone never does.

**See who still carries it.** ``--kind retire`` filters to the
retirement kinds:

::

    $ drift-doctor detect --kind retire

    ── alpha: 2 finding(s)
      retire.measure               Classes[Class Fill Rate %]
      retire.column                Classes[Capacity]  [not allowlisted] [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left]

    ── summary: actionable=1 advisory=0 overridden=0 errors=0

Bravo has no ``Classes`` table, so it has nothing to remove. Two things
stand in alpha's way:

- The example allowlist names ``retire.measure`` but not
  ``retire.column``, so the column prints ``[not allowlisted]``. Add it
  under ``allowlist.kinds`` in ``fleet.yml``:

  ::

      allowlist:
        kinds:
          ...
          - retire.measure
          - retire.column

- The column is ``[blocked]``: alpha's own measure ``Alpha Seats Left``
  reads it, and a retirement never removes something the model's own
  work depends on. A person decides: rewrite or remove the dependent,
  or keep the column with a ``retain`` override or a revival.

**Preview it.** Retirements are deletions, so they are double-gated:
the kind must be allowlisted and the run must pass ``--sync``. Without
``--sync`` the run skips them:

::

    $ drift-doctor remediate --kind retire --dry-run
    [skipped] alpha: retire.measure Classes[Class Fill Rate %] — retirement and purge items require --sync (they never run in a default pass) — re-run with --sync to apply this
    [skipped] alpha: retire.column Classes[Capacity] — retirement and purge items require --sync (they never run in a default pass) — re-run with --sync to apply this
    ...

With ``--sync``:

::

    $ drift-doctor remediate --kind retire --sync --dry-run
    [would apply] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block [destructive: asked, never under --yes]
    --- a//tmp/gym-fleet/derived/alpha/GymChain.SemanticModel/definition/tables/Classes.tmdl
    +++ b//tmp/gym-fleet/derived/alpha/GymChain.SemanticModel/definition/tables/Classes.tmdl
    @@ -19,10 +19,6 @@
     		summarizeBy: sum
     		sourceColumn: Capacity

    -	measure 'Class Fill Rate %' = DIVIDE(COUNTROWS(Visits), SUM(Classes[Capacity]))
    -		formatString: 0.0%
    -		lineageTag: 33333333-3333-4333-8333-000000000005
    -
     	/// Alpha's own seat-availability KPI.
     	measure 'Alpha Seats Left' = SUM(Classes[Capacity]) - COUNTROWS(Visits)
     		formatString: #,0

    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: derived-only definition(s) reference it: Classes[Alpha Seats Left]. Decide by hand: remove or rewrite the dependent, or keep the object with a `retain` override or a ledger revival.

    ── summary: applied=0 would-apply=1 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...

**Apply it on a terminal.** The question says the fix is destructive:

::

    $ drift-doctor remediate --kind retire --sync
    [1/2] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block. DESTRUCTIVE (deletes derived-model content). Apply? [y/n/a/q] y
    [applied] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block
    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: derived-only definition(s) reference it: Classes[Alpha Seats Left]. Decide by hand: remove or rewrite the dependent, or keep the object with a `retain` override or a ledger revival.

    ── summary: applied=1 would-apply=0 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...

**Or apply it from a scheduled job.** Without a terminal, ``--sync``
alone writes nothing and says why, and ``--yes`` does not help either:
a deletion is never applied under ``--yes``.

::

    $ drift-doctor remediate --kind retire --sync < /dev/null
    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [skipped] alpha: retire.measure Classes[Class Fill Rate %] — destructive: deletions are never applied under --yes or in batch mode; answer interactively, or pass --sync with --confirm-deletions
    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: ...

    ── summary: applied=0 would-apply=0 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=1 skipped_noninteractive=0 failed=0
    ...

The scheduled-job form adds ``--confirm-deletions``, the explicit
second confirmation:

::

    # bash / macOS / Linux
    drift-doctor remediate --kind retire --sync --confirm-deletions < /dev/null

::

    # PowerShell / Windows
    $null | drift-doctor remediate --kind retire --sync --confirm-deletions

::

    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [applied] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block
    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: ...

    ── summary: applied=1 would-apply=0 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...

A plain ``drift-doctor remediate`` (no ``--sync``) skips every
``retire.*`` finding with the reason shown above; a default pass only
adds and overwrites.

**Verify**, then note the edge cases:

::

    # bash / macOS / Linux
    drift-doctor detect --kind retire
    drift-doctor ledger | tail

::

    # PowerShell / Windows
    drift-doctor detect --kind retire
    drift-doctor ledger | Select-Object -Last 10

- The run is idempotent: a second ``--sync`` pass finds nothing more to
  remove.
- A derived model that never had the column is untouched (no finding).
- If a model's own measures, relationships, sort-by columns or
  hierarchy levels still use the column, the removal is ``blocked`` and
  ``detect`` names the dependent. Report visuals are not checked; search
  them yourself before removing a measure or column a report may bind.
- If a template measure in the model still reads the column (its
  expression drift was never cascaded), the removal waits as
  ``auto_skipped_precondition`` until that overwrite lands. With
  ``measure.expression_drift`` allowlisted, one ``--sync`` run does
  both, in order.
- If one franchise must keep the object, revive it for that model first
  (section 3), or declare a ``retain`` override.

3. Recover from an unwanted removal
---------------------------------------

Goal: a ``--sync`` pass removed an object that one derived model was
supposed to keep. Put it back, and make sure no later pass removes it
again. The transcripts continue from section 2.

**Find out exactly what happened.** The ledger records every
retirement and every applied fix:

::

    # bash / macOS / Linux
    drift-doctor ledger | grep "Class Fill Rate"

::

    # PowerShell / Windows
    drift-doctor ledger | Select-String "Class Fill Rate"

::

    2026-10-22T16:32:39+00:00  retired  measure  Classes[Class Fill Rate %]
    2026-10-22T16:33:22+00:00  remediated  retire.measure  model=alpha  Classes[Class Fill Rate %]  — remove retired measure block

``drift-doctor ledger --json`` prints the raw events, including the
files each fix touched:

::

    {"ts": "2026-10-22T16:33:22+00:00", "event": "remediated", "kind": "retire.measure", "model": "alpha", "ref": "Classes[Class Fill Rate %]", "action": "remove retired measure block", "files": ["/tmp/gym-fleet/derived/alpha/GymChain.SemanticModel/definition/tables/Classes.tmdl"]}

**Restore the object.** Put the block back in the model's table file.
Version control is the natural source (``git checkout -- <table
file>``, or copy the block from history); otherwise paste it back by
hand. ``detect`` then reports it again, because the retirement is
still in force:

::

    $ drift-doctor detect --kind retire

    ── alpha: 2 finding(s)
      retire.measure               Classes[Class Fill Rate %]
      retire.column                Classes[Capacity]  [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left]

    ── summary: actionable=2 advisory=0 overridden=0 errors=0

``drift-doctor audit`` reports the undone fix and exits 4:

::

    $ drift-doctor audit
    [REVERTED] alpha: retire.measure Classes[Class Fill Rate %] (applied 2026-10-22T16:33:22+00:00) — retired measure Classes[Class Fill Rate %] was removed by this fix and is back
    ── audit: checked=1 ok=0 reverted=1 superseded=0 error=0

**Revive it for that model.** A revival is an append-only ledger event
that cancels the retirement without erasing its history. Scope it to
the model that keeps the object (``--kind`` is the retirement kind:
``table``, ``column``, ``measure``, ``mapping_row``,
``mapping_category`` or ``relationship``):

::

    $ drift-doctor ledger --revive "Classes[Class Fill Rate %]" --kind measure --model alpha --note "alpha keeps its class fill-rate KPI"
    revived measure Classes[Class Fill Rate %] for model 'alpha' — it will not be re-removed.

The finding is gone, and the run says what it did about it:

::

    $ drift-doctor detect --kind retire
    [decision] alpha: measure Classes[Class Fill Rate %] — revived (manual); retirement skipped

    ── alpha: 1 finding(s)
      retire.column                Classes[Capacity]  [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left], Classes[Class Fill Rate %]

    ── summary: actionable=1 advisory=0 overridden=0 errors=0

The audit now reads the fix as ``superseded``, not reverted, and exits 0:

::

    $ drift-doctor audit
    [superseded] alpha: retire.measure Classes[Class Fill Rate %] (applied 2026-10-22T16:33:22+00:00) — revived or retained since the removal
    ── audit: checked=1 ok=0 reverted=0 superseded=1 error=0

Omit ``--model`` to revive for the whole fleet, for example when the
retirement itself was a mistake:

::

    $ drift-doctor ledger --revive "Classes[Capacity]" --kind column
    revived column Classes[Capacity] for the whole fleet — it will not be re-removed.

A revival of something that has no retirement in force is refused with
exit 1, because it is usually a typo:

::

    $ drift-doctor ledger --revive "Classes[Nope]" --kind column
    Error: no active retirement found for column 'Classes[Nope]'. Run `drift-doctor ledger` to list retirement events and check the reference and kind — this usually means a typo.

**Verify** that no later pass removes it again; the dry run lists both
revivals as decisions and applies nothing:

::

    $ drift-doctor remediate --kind retire --sync --dry-run
    [decision] alpha: measure Classes[Class Fill Rate %] — revived (manual); retirement skipped
    [decision] alpha: column Classes[Capacity] — revived (manual); retirement skipped

    ── summary: applied=0 would-apply=0 skipped=0 manual=0 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0
    ...

Notes:

- A model-scoped revival protects exactly one model; other models
  still carrying the object stay on the removal path.
- If the object later returns to the template, the next ``capture``
  records a fleet-wide revival and normal comparison resumes.
- Never edit or delete ledger lines to undo something; the ledger is
  append-only by design. Every correction is a new event.
