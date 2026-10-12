Manage a fleet
=================

Three recurring tasks once a fleet is running: bring a new model under
management, cascade a retirement all the way through, and undo a
remediation that removed something a client still needed.

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

Then cascade one kind at a time rather than everything at once:

::

    $ drift-doctor remediate --model charlie --kind measure.missing --dry-run
    $ drift-doctor remediate --model charlie --kind measure.missing
    $ drift-doctor remediate --model charlie --kind measure.expression_drift --dry-run
    ...

Once you trust the kinds, ``drift-doctor remediate --model charlie
--converge`` runs them all and re-detects until nothing changes.

If objects were retired from the template before charlie joined the
fleet, the ledger already lists them, and ``detect`` flags any that
charlie still carries as ``retire.*``. Decide per object: retired
debris gets ``drift-doctor remediate --model charlie --sync``;
something deliberately kept gets revived for charlie only:

::

    $ drift-doctor ledger --revive "Visits[Peak Hour Visits]" --kind measure --model charlie

Caveats:

- ``table.missing`` copies the template's partition source verbatim. If
  the new model reads a different source, fix the partition after the
  cascade.
- Adding a model never requires a recapture; the baseline describes the
  template, not the fleet.

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
    baseline written: .drift-doctor/baseline.json
      ...
      [ledger] retired column: Classes[Capacity]

This does two things at once. The baseline stops listing the column;
without this step, ``detect`` would flag every derived model as
``column.missing`` and the missing-object cascade would resurrect the
column from a template that no longer has it. And the recapture diff
(previous baseline against the fresh snapshot) proves the column used
to be in the template, appending a ``retired`` event to the ledger.
That proof is what authorizes the removal; absence alone never does.

See who still carries it:

::

    $ drift-doctor detect --kind retire.
    -- alpha: 1 finding(s)
      retire.column                Classes[Capacity]  [blocked]
          blocked:  derived-only definition(s) reference it: Classes[Alpha Seats Left]
    -- bravo: 1 finding(s)
      retire.column                Classes[Capacity]

(This is the example fleet after a full remediation: alpha's own
``Alpha Seats Left`` measure still reads the column, so its removal is
refused until a person decides.)

Retirements are deletions, so they are double-gated: the kind must be
in the allowlist (``retire.column``) and the run must opt in with
``--sync``:

::

    $ drift-doctor remediate --kind retire.column --sync --dry-run   # preview
    $ drift-doctor remediate --kind retire.column --sync
    [BLOCKED] alpha: retire.column Classes[Capacity] - derived work depends on it: ...
    [applied] bravo: retire.column Classes[Capacity] - remove retired column block

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

    $ drift-doctor ledger | grep "Peak Hour Visits"
    2026-...  retired     measure  Visits[Peak Hour Visits]
    2026-...  remediated  retire.measure  model=alpha  Visits[Peak Hour Visits] - remove retired measure block

Restore the object: re-add it to the derived model. Version control is
the natural source (``git checkout -- <table file>`` or copy the block
from history); otherwise paste the block back by hand. At this point
``detect`` flags it again, since the retirement is still active in the
ledger:

::

    $ drift-doctor detect --kind retire.
    -- alpha: 1 finding(s)
      retire.measure               Visits[Peak Hour Visits]

Revive it. A revival is an append-only ledger event that cancels the
retirement without erasing its history. Scope it to the one model that
keeps the object:

::

    $ drift-doctor ledger --revive "Visits[Peak Hour Visits]" --kind measure \
        --model alpha --note "alpha keeps its evening-peak KPI"
    revived measure Visits[Peak Hour Visits] for model 'alpha'; it will not be re-removed.

Omit ``--model`` to revive fleet-wide, for example when the retirement
itself was a mistake. Verify:

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
