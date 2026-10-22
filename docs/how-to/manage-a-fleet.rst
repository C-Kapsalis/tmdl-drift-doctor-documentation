Manage a fleet
=================

Three recurring tasks once a fleet is running: bring a new model under
management, cascade a retirement all the way through, and undo a
remediation that removed something a client still needed.

.. important::

   **One thing to know before you run any of this:** ``remediate``
   confirms every fix with a question, and a question needs a terminal.
   On a terminal the run asks; everywhere else — a script, a pipe, a CI
   job, an IDE agent — the questions are disabled, every item is treated
   as a "no", and **nothing is applied**. The run says so once::

       note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.

   So the two forms are:

   - on a terminal, ``drift-doctor remediate`` (add ``--sync`` for
     deletions);
   - in a script, ``drift-doctor remediate --yes --kind <kind>`` for
     the batch-safe kinds, and ``--sync --confirm-deletions`` for the
     deletions.

   Every command in this page is shown in both forms where the
   difference matters.

1. Add a model to the fleet
-------------------------------

Goal: bring a new derived model under drift management.

The model must be a TMDL-format ``.SemanticModel`` folder with a
``definition/`` directory (``tables/*.tmdl``, ``model.tmdl``,
optionally ``expressions.tmdl``). Location is up to you; paths in
``fleet.yml`` are resolved relative to the fleet file. Register it under
``models:``:

::

    models:
      alpha: franchises/alpha/GymChain.SemanticModel
      bravo: franchises/bravo/GymChain.SemanticModel
      charlie: franchises/charlie/GymChain.SemanticModel   # new

``load_fleet`` validates the path on the next run; a missing
``definition/`` directory fails loudly rather than silently skipping
the model.

Take stock before fixing anything. Run a scoped, read-only detection
first:

::

    $ drift-doctor detect --model charlie

A model that lived away from the template for a while can carry a lot
of drift. Read the findings before remediating:

- Missing objects are usually safe to cascade.
- Expression and property drift overwrite the derived version; check
  the diffs with ``--dry-run`` in case the divergence was deliberate.
  If it was, declare it as an override on the model's entry (below).
- Extras are advisory; nothing touches them.

Record every deliberate difference as an override instead of leaving it
as standing drift. Switch the model to the long form:

::

    models:
      charlie:
        path: franchises/charlie/GymChain.SemanticModel
        gating: advisory            # optional, while onboarding
        overrides:
          - object: Visits[Total Visits]
            kind: expression        # keeps its own definition
            reason: charlie excludes zero-minute visits by contract
            owner: charlie-analytics
            added: 2026-10-12

``gating: advisory`` keeps a freshly onboarded model from failing
``detect`` and the ratchet while its backlog is worked down; switch it
back to ``enforced`` (or drop the key) once it is clean, then record its
floor with ``drift-doctor ratchet tighten --allow-new``.

Then cascade one kind at a time rather than everything at once. On a
terminal, answer each question; in a script, name the kind and pass
``--yes``:

::

    $ drift-doctor remediate --model charlie --kind measure.missing --dry-run
    $ drift-doctor remediate --model charlie --kind measure.missing
    $ drift-doctor remediate --model charlie --kind measure.expression_drift --dry-run
    ...

::

    $ drift-doctor remediate --model charlie --kind measure.missing --yes
    $ drift-doctor remediate --model charlie --kind measure.expression_drift --yes
    ...

Without the terminal, the first form applies nothing and says so:

::

    $ drift-doctor remediate --model charlie --kind measure.missing < /dev/null
    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [skipped] charlie: measure.missing Members[New Members #] — non-interactive: not applied without --yes
    ...
    ── summary: applied=0 would-apply=0 skipped=1 manual=0 blocked=0 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=1 failed=0

Once you trust the kinds, ``drift-doctor remediate --model charlie
--converge`` runs them all and re-detects until nothing changes.

If objects were retired from the template before charlie joined the
fleet, the ledger already lists them, and ``detect`` flags any that
charlie still carries as ``retire.*``. Decide per object: retired
debris gets ``drift-doctor remediate --model charlie --sync`` (with
``--yes --kind retire.`` from a script, or
``--sync --confirm-deletions``); something deliberately kept gets
revived for charlie only:

::

    $ drift-doctor ledger --revive "Visits[Peak Hour Visits]" --kind measure --model charlie

Caveats:

- ``table.missing`` copies the template's partition source verbatim. If
  the new model reads a different source, fix the partition after the
  cascade.
- Adding a model never requires a recapture; the baseline describes the
  template, not the fleet.
- ``--yes`` never deletes anything. A retirement is a deletion, so it
  needs an interactive yes or ``--sync --confirm-deletions``.

2. Cascade a column retirement
----------------------------------

Goal: a column was removed from the template, and every derived model
that still carries it should drop it too.

This walkthrough uses a column, but the flow is identical for measures,
whole tables, and mapping rows; they are all retirement kinds.

Retire the column in the template first: edit the template's table
file and delete the column block (declaration line plus its two-tab
properties and annotations), and remove any template measures that
referenced it, so the template stays self-consistent. Then recapture
immediately:

::

    $ drift-doctor capture
    baseline written: /tmp/gym-fleet/.drift-doctor/baseline.json
      tables=5 columns=16 measures=8 relationships=3 mapping_rows=4 expressions=3
      [ledger] retired column: Classes[Capacity]
      [ledger] retired measure: Classes[Class Fill Rate %]

Two retirements, because the measure that read the column went with it.
Both are retirement kinds, and both need the same treatment below.

This does two things at once. The baseline stops listing the column;
without this step, ``detect`` would flag every derived model as
``column.missing`` and the missing-object cascade would resurrect the
column from a template that no longer has it. And the recapture diff
(previous baseline against fresh snapshot) proves the column used
to be in the template, appending a ``retired`` event to the ledger.
That proof is what authorizes the removal; absence alone never does.

See who still carries it:

::

    $ drift-doctor detect --kind retire.

    ── alpha: 2 finding(s)
      retire.measure               Classes[Class Fill Rate %]
      retire.column                Classes[Capacity]  [not allowlisted] [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left]

    ── summary: actionable=1 advisory=0 overridden=0 errors=0

(The example fleet's starter allowlist names ``retire.measure`` but not
``retire.column``; that is why the column prints ``[not allowlisted]``.
Add it before the run below.)

Retirements are deletions, so they are double-gated: the kind must be
in the allowlist (``retire.column``) and the run must opt in with
``--sync``. A deletion also needs its own confirmation, which is what
``--confirm-deletions`` is for in a scheduled job.

Preview it:

::

    $ drift-doctor remediate --kind retire. --sync --dry-run
    [would apply] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block [destructive: asked, never under --yes]
    --- a/.../derived/alpha/GymChain.SemanticModel/definition/tables/Classes.tmdl
    +++ b/.../derived/alpha/GymChain.SemanticModel/definition/tables/Classes.tmdl
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

Then apply it. On a terminal the deletion is asked for, and the
question says it is destructive:

::

    $ drift-doctor remediate --kind retire. --sync
    [1/2] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block. DESTRUCTIVE (deletes derived-model content). Apply? [y/n/a/q] y
    [applied] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block
    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: derived-only definition(s) reference it: Classes[Alpha Seats Left]. Decide by hand: remove or rewrite the dependent, or keep the object with a `retain` override or a ledger revival.

    ── summary: applied=1 would-apply=0 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0

From a script, the same command applies nothing, and the run says
exactly why:

::

    $ drift-doctor remediate --kind retire. --sync < /dev/null
    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [skipped] alpha: retire.measure Classes[Class Fill Rate %] — destructive: deletions are never applied under --yes or in batch mode; answer interactively, or pass --sync with --confirm-deletions
    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: derived-only definition(s) reference it: Classes[Alpha Seats Left]. Decide by hand: remove or rewrite the dependent, or keep the object with a `retain` override or a ledger revival.

    ── summary: applied=0 would-apply=0 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=1 skipped_noninteractive=0 failed=0

``--yes`` does not help here: a deletion is never applied under
``--yes``. The scheduled-job form is ``--sync`` together with
``--confirm-deletions``:

::

    $ drift-doctor remediate --kind retire. --sync --confirm-deletions < /dev/null
    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.
    [applied] alpha: retire.measure Classes[Class Fill Rate %] — remove retired measure block
    [BLOCKED] alpha: retire.column Classes[Capacity] — derived work depends on it: derived-only definition(s) reference it: Classes[Alpha Seats Left]. Decide by hand: remove or rewrite the dependent, or keep the object with a `retain` override or a ledger revival.

    ── summary: applied=1 would-apply=0 skipped=0 manual=0 blocked=1 auto_skipped_precondition=0 overridden=0 skipped_override=0 skipped_divergent=0 skipped_destructive=0 skipped_noninteractive=0 failed=0

A plain ``drift-doctor remediate`` (no ``--sync``) skips every
``retire.*`` finding with an explanatory reason; a default pass is
purely additive or overwriting.

Verify, then note the edge cases:

::

    $ drift-doctor detect --kind retire.
    $ drift-doctor ledger | tail

- The run is idempotent: a second ``--sync`` pass finds nothing to
  remove.
- A derived model that never had the column is untouched (no finding).
- If a derived model's own measures, relationships, sort-by columns, or
  hierarchy levels still use the dropped column, the removal is
  ``blocked`` and ``detect`` says which object depends on it. Rewrite or
  remove the dependent, or keep the column with a ``retain`` override.
  Report visuals are not checked; search them yourself.
- If a template measure in the derived model still reads the column
  (its expression drift was never cascaded), the removal waits as
  ``auto_skipped_precondition`` until that overwrite lands. With
  ``measure.expression_drift`` allowlisted, one ``--sync`` run does
  both, in order.
- If one franchise must keep the column, revive it for that model
  first (section 3, below), or declare a ``retain`` override.

3. Recover from an unwanted remediation
--------------------------------------------

Goal: a ``--sync`` pass removed an object that one derived model was
supposed to keep. Put it back, and make sure no future pass removes it
again.

Find out exactly what happened. The ledger records every applied
action with the files it touched:

::

    $ drift-doctor ledger | grep "Class Fill Rate"
    2026-10-22T15:09:55+00:00  retired  measure  Classes[Class Fill Rate %]
    2026-10-22T15:09:55+00:00  remediated  retire.measure  model=alpha  Classes[Class Fill Rate %]  — remove retired measure block

Restore the object: re-add it to the derived model. Version control is
the natural source (``git checkout -- <table file>`` or copy the block
from history); otherwise paste the block back by hand. At this point
``detect`` flags it again, since the retirement is still active in the
ledger:

::

    $ drift-doctor detect --kind retire.

    ── alpha: 2 finding(s)
      retire.measure               Classes[Class Fill Rate %]
      retire.column                Classes[Capacity]  [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left]

    ── summary: actionable=2 advisory=0 overridden=0 errors=0

``drift-doctor audit`` also says so, and exits 4:

::

    $ drift-doctor audit
    [REVERTED] alpha: retire.measure Classes[Class Fill Rate %] (applied 2026-10-22T15:09:55+00:00) — retired measure Classes[Class Fill Rate %] was removed by this fix and is back
    ── audit: checked=1 ok=0 reverted=1 superseded=0 error=0

Revive it. A revival is an append-only ledger event that cancels the
retirement without erasing its history. Scope it to the one model that
keeps the object:

::

    $ drift-doctor ledger --revive "Classes[Class Fill Rate %]" --kind measure \
        --model alpha --note "alpha keeps its evening-peak KPI"
    revived measure Classes[Class Fill Rate %] for model 'alpha' — it will not be re-removed.

The finding is gone from alpha, and the run says what it did about it:

::

    $ drift-doctor detect --kind retire.
    [decision] alpha: measure Classes[Class Fill Rate %] — revived (manual); retirement skipped

    ── alpha: 1 finding(s)
      retire.column                Classes[Capacity]  [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left], Classes[Class Fill Rate %]

    ── summary: actionable=1 advisory=0 overridden=0 errors=0

Omit ``--model`` to revive fleet-wide, for example when the retirement
itself was a mistake:

::

    $ drift-doctor ledger --revive "Classes[Capacity]" --kind column
    revived column Classes[Capacity] for the whole fleet — it will not be re-removed.

Verify that no future pass removes it again:

::

    $ drift-doctor detect --kind retire.     # no finding for alpha
    $ drift-doctor remediate --sync          # will not re-remove it

Other models still carrying the object remain flagged; a model-scoped
revival protects exactly one model.

Notes:

- If the object later returns to the template, the next ``capture``
  auto-revives it fleet-wide and normal drift comparison resumes.
- Never edit or delete ledger lines to undo something; the ledger is
  append-only by design. Every correction is a new event.
