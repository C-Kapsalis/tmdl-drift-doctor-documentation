Run in CI
=========

Goal: make drift a build signal. Every push tells you whether the fleet
still matches the template, whether drift grew, and whether an applied
fix was quietly undone, without CI ever mutating a model.

The contract
---------------

Every gate command is read-only:

- ``drift-doctor detect`` exits ``0`` when nothing is actionable
  (only advisories, non-allowlisted kinds, overridden findings, or
  findings on ``gating: advisory`` models), ``1`` when actionable
  drift exists, ``2`` when the configuration is broken or the baseline
  is stale, and ``3`` when a model could not be parsed. A stale
  baseline (the template changed without a recapture) fails with a
  message, which is a feature: a pull request that edits the template
  but forgets ``drift-doctor capture`` fails loudly instead of
  producing wrong findings. It exits **2**, not 1, so the job can tell
  "the run could not be done" from "the model has drift".
- ``drift-doctor ratchet check`` exits ``1`` when any model's drift
  rose above its floor or a retired object is in a model, and ``2``
  when it cannot trust its input.
- ``drift-doctor audit`` exits ``4`` when an applied fix was reverted.

What to commit
------------------

Commit the state directory alongside the models:

- ``.drift-doctor/baseline.json``: CI needs the committed template
  truth; capturing inside CI would compare the template against
  itself.
- ``.drift-doctor/ledger.jsonl``: retirements, revivals, and applied
  fixes are shared fleet state, and ``audit`` reads them.
- ``.drift-doctor/floors.json``: the ratchet floors.

Gate on the ratchet, not on zero drift
------------------------------------------

A real fleet rarely reaches zero drift, so a plain ``detect`` gate is
either red all the time or switched off. The ratchet gates on "did this
change make drift worse" instead.

1. Seed the floors once, from a full-fleet run, and commit the file:

   ::

       $ drift-doctor ratchet tighten
         alpha: recorded at 6
         bravo: recorded at 6
       floors written: /tmp/gym-fleet/.drift-doctor/floors.json

2. Make ``ratchet check`` the required check on pull requests. It fails
   when any model's actionable count rises, in total or for any single
   **kind head**, and names the model and the head:

   ::

       $ drift-doctor ratchet check
       [RISE] alpha: TOTAL rose 5 -> 6
       [RISE] alpha: category 'column' rose 0 -> 1
       [RISE] bravo: TOTAL rose 6 -> 7
       [RISE] bravo: category 'column' rose 2 -> 3
         alpha: column 1 (column.missing 1)
         alpha: expression 2 (expression.drift 2)
         alpha: measure 3 (measure.expression_drift 1, measure.property_drift 1, measure.wrong_host 1)
         bravo: column 3 (column.missing 2, column.property_drift 1)
         bravo: mapping_row 1 (mapping_row.missing 1)
         bravo: relationship 2 (relationship.missing 1, relationship.modified 1)
         bravo: table 1 (table.missing 1)
       no ledger-retired object resurrected
       DRIFT RATCHET RED

   The floor is counted per **kind head** — the text before the first
   dot. ``measure.missing`` and ``measure.expression_drift`` both roll
   up to ``measure``, so one measure finding of any kind raises the
   same head. The floors file records it as ``by_category``; a
   version-1 file keyed by kind is read as-is and rolled up on load, and
   the next ``tighten`` rewrites it in head form.

   What counts is every finding a sync could act on, whatever
   ``allowlist.kinds`` says, minus overridden findings, advisory and
   report-only kinds, and the model-intrinsic regenerations
   (``ifilter.*``, ``visibility.*``, ``ffilter.coverage_gap``). The
   allowlist decides what ``remediate`` writes, never what the ratchet
   counts.

3. After remediation lands, run ``ratchet tighten`` and commit the
   lowered floors in the same change. ``tighten`` never raises a floor.

   ::

       $ drift-doctor ratchet tighten
         alpha: 6 -> 5
       floors written: /tmp/gym-fleet/.drift-doctor/floors.json

4. Never raise a floor by hand without saying why in the change that
   does it. Floors measure debt; a raised floor is new debt someone
   agreed to.

Two rules are stricter than a floor:

- **Resurrections are hard zero.** A ``retire.*`` finding means an
  object the ledger proves was retired from the template is still or
  again in a model, typically from a branch whose base predates the
  retirement. It is never floored and fails ``check`` by name, in its
  own block:

  ::

      RESURRECTION — ledger-retired objects are back (hard zero, never floored):
        alpha: retire.measure Classes[Class Fill Rate %]
        alpha: cascade it with `drift-doctor remediate --model alpha --kind retire --sync`, or declare a `retain` override
      ...
    DRIFT RATCHET RED — RESURRECTION

  Clear it with a ``--sync`` remediation, or declare a ``retain``
  override if the model must keep it. ``--include-advisory`` extends
  the hard zero to a retirement that no sync can apply.
- **Provenance is checked.** ``tighten`` only accepts a full-fleet,
  unfiltered, error-free report; ``check`` also refuses kind-filtered
  and errored reports.

Models marked ``gating: advisory`` in ``fleet.yml`` are reported in
their own block and never fail the check, so a model that is still
being onboarded cannot wedge the gate shut.

Audit applied fixes
-----------------------

Fixes can be undone after they land: a hand edit, a merge whose stale
side won a conflict, a Desktop re-save. Schedule ``drift-doctor audit``
(nightly is plenty). It re-verifies every applied fix in the ledger and
exits ``4`` on a revert, naming the model, kind, and object.

Publish the review queue
----------------------------

``drift-doctor review --out REVIEW.md`` writes the checklist of
everything the rules route to a human: blocked retirements,
precondition skips, wrong or duplicate hosts, advisories, and overrides
in force. Upload it as an artifact so the queue is visible without
anyone running the tool locally. Anything that keeps reappearing there
is a missing rule; encode it once.

GitHub Actions example
--------------------------

::

    name: drift-gate
    on: [push, pull_request]

    jobs:
      drift:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: "3.12"
          - run: pip install ./tools/tmdl-drift-doctor
          - name: Detect drift (read-only report)
            run: drift-doctor detect --fleet fleet.yml --json > drift.json || true
          - name: Ratchet gate
            run: drift-doctor ratchet check --fleet fleet.yml --from-json drift.json
          - name: Audit applied fixes
            run: drift-doctor audit --fleet fleet.yml
          - name: Review queue
            if: always()
            run: drift-doctor review --fleet fleet.yml --out REVIEW.md
          - name: Upload findings
            if: always()
            uses: actions/upload-artifact@v4
            with:
              name: drift-report
              path: |
                drift.json
                REVIEW.md

The ``|| true`` keeps the detect step from failing the job on its own,
so the ratchet decides; drop it to gate on zero actionable drift
instead. If detection hits a parse error, the report's ``errors`` list
is non-empty and ``ratchet check`` refuses it with exit ``2``.

Policy choices
-----------------

**Warn-only versus gate.** Drift is often expected backlog. The ratchet
is the middle ground: backlog may stay, it may not grow. A stricter
option is a zero-drift ``detect`` gate on pull requests that touch the
template, since those are the ones that create new drift:

::

          - name: Gate template PRs
            if: contains(github.event.pull_request.changed_files, 'template/')
            run: drift-doctor detect --fleet fleet.yml

**Never remediate in CI.** ``remediate`` belongs in a maintainer's
working tree, where the diffs get reviewed and committed deliberately.
This is not a style preference: ``remediate`` confirms every fix with
a question, and a CI job has no terminal, so a bare ``remediate`` in a
job applies **nothing** and says so::

    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.

If you want automated fix-up pull requests, run ``remediate --dry-run``
in CI, post the diff for review, and keep the actual write on a
human's machine. A job that does write has to name the kinds and say
that it means it::

    drift-doctor remediate --yes --kind measure.missing

and even then it never deletes anything: a deletion needs an
interactive yes, or ``--sync`` together with
``--confirm-deletions``.

**Scoped checks.** ``--model`` and ``--kind`` narrow ``detect``, for
example a nightly job that only watches retirements. Scoped reports are
fine to read, but never feed a kind-filtered report to the ratchet:

::

    $ drift-doctor detect --kind retire. --json
