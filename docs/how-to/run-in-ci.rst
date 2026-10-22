Run in CI
=========

Goal: make drift a build signal. Every push tells you whether the fleet
still matches the template, whether drift grew, and whether an applied
fix was quietly undone, without CI ever changing a model. The
transcripts were produced by ``drift-doctor`` 1.2.1 on a git-tracked
copy of the example fleet from :doc:`../tutorials/getting-started`.

The contract
---------------

Every gate command is read-only, and each exit code means one thing:

- ``drift-doctor detect`` exits ``0`` when nothing is actionable (only
  advisories, non-allowlisted kinds, overridden findings, or findings
  on ``gating: advisory`` models), ``1`` when actionable drift exists,
  ``2`` when the configuration is broken or the baseline is stale, and
  ``3`` when a model could not be parsed.
- ``drift-doctor ratchet check`` exits ``1`` when a model's drift rose
  above its floor, a model has no floor, or a retired object is back in
  a model, and ``2`` when it cannot trust its input.
- ``drift-doctor audit`` exits ``4`` when an applied fix was undone, and
  ``3`` when a model could not be parsed.

A stale baseline (the template changed without a recapture) fails with
exit **2**, not 1, so a job can tell "the run could not be done" from
"the model has drift". A pull request that edits the template but
forgets ``drift-doctor capture`` fails loudly instead of producing
wrong findings:

::

    $ drift-doctor detect
    Error: the template has changed since the last capture — the committed baseline is stale, and findings computed against it can be misclassified (a retired object would look missing and be resurrected). Run `drift-doctor capture` before detecting or remediating; --allow-stale proceeds anyway if you accept that risk.

What to commit
------------------

Commit the state directory (``.drift-doctor`` by default) alongside the
models:

- ``baseline.json``: CI needs the committed template truth; capturing
  inside CI would compare the template against itself.
- ``ledger.jsonl``: retirements, revivals and applied fixes are shared
  fleet state, and ``audit`` and ``freshness`` read them.
- ``floors.json``: the ratchet floors.

The full list of state files, and which ones to commit, is in
:doc:`../reference/cli-and-configuration`.

Gate on the ratchet, not on zero drift
------------------------------------------

A real fleet rarely reaches zero drift, so a plain ``detect`` gate is
either red all the time or switched off. The ratchet asks "did this
change make drift worse" instead.

1. Seed the floors once, from a full-fleet run, and commit the file:

   ::

       $ drift-doctor ratchet tighten
         alpha: recorded at 6
         bravo: recorded at 6
       floors written: /tmp/gym-fleet/.drift-doctor/floors.json

2. Make ``ratchet check`` the required check on pull requests. Here a
   change deleted the ``PromoName`` column from alpha's ``Promotions``
   table:

   ::

       $ drift-doctor ratchet check
       [RISE] alpha: TOTAL rose 6 -> 7
       [RISE] alpha: category 'column' rose 0 -> 1
         alpha: column 1 (column.missing 1)
         alpha: expression 2 (expression.drift 2)
         alpha: measure 4 (measure.expression_drift 1, measure.missing 1, measure.property_drift 1, measure.wrong_host 1)
         bravo: column 2 (column.missing 1, column.property_drift 1)
         bravo: mapping_row 1 (mapping_row.missing 1)
         bravo: relationship 2 (relationship.missing 1, relationship.modified 1)
         bravo: table 1 (table.missing 1)
       no ledger-retired object resurrected
       DRIFT RATCHET RED

   The floor is counted in total and per **kind head**, the text before
   the first dot: ``measure.missing`` and ``measure.expression_drift``
   both count toward ``measure``. The floors file stores the heads under
   ``by_category``.

   What counts is every finding a sync could act on, whatever
   ``allowlist.kinds`` says, minus overridden findings, advisory and
   report-only kinds, and the model-intrinsic regenerations
   (``ifilter.*``, ``visibility.*``, ``ffilter.coverage_gap``). The
   allowlist decides what ``remediate`` writes, never what the ratchet
   counts. That is why bravo's two ``model.count_below_template``
   findings, which ``detect`` counts as actionable, are not in its
   floor of 6.

3. After a fix lands, run ``ratchet tighten`` and commit the lowered
   floors in the same change. Here alpha's missing measure was fixed:

   ::

       $ drift-doctor ratchet tighten
         alpha: 6 -> 5
       floors written: /tmp/gym-fleet/.drift-doctor/floors.json

   ``tighten`` never raises a floor. Raising one is a hand edit of the
   file, made in the change that justifies it: a raised floor is new
   debt someone agreed to.

Two rules are stricter than a floor:

- **Resurrections are hard zero.** A ``retire.*`` finding means an
  object the ledger proves was retired from the template is still, or
  again, in a model; typically a branch whose base predates the
  retirement. It is never floored, and it fails ``check`` by name in its
  own block. Here the template retired ``Peak Hour Visits`` and both
  franchises still carry it:

  ::

      $ drift-doctor ratchet check
      RESURRECTION — ledger-retired objects are back (hard zero, never floored):
        alpha: retire.measure Visits[Peak Hour Visits]
        alpha: cascade it with `drift-doctor remediate --model alpha --kind retire --sync`, or declare a `retain` override
        bravo: retire.measure Visits[Peak Hour Visits]
        bravo: cascade it with `drift-doctor remediate --model bravo --kind retire --sync`, or declare a `retain` override
        ...
      DRIFT RATCHET RED — RESURRECTION

  Clear it with a ``--sync`` remediation (see
  :doc:`manage-a-fleet`), or declare a ``retain`` override if the
  model must keep it. ``--include-advisory`` extends the hard zero to a
  retirement that no sync can apply.
- **The input is checked.** ``check`` and ``tighten`` refuse (exit 2) a
  report filtered with ``--kind``, a report that carries detection
  errors, and a report with a schema version other than 2. ``tighten
  --prune`` also needs a full-fleet report.

Models marked ``gating: advisory`` in ``fleet.yml`` are reported in
their own block and never fail the check, so a model that is still
being onboarded cannot hold the gate shut.

Audit applied fixes
-----------------------

Fixes can be undone after they land: a hand edit, a merge whose stale
side won a conflict, a Desktop re-save. Schedule ``drift-doctor
audit`` (nightly is plenty). It re-checks every applied fix in the
ledger that added, moved or removed an object, and exits ``4`` on a
revert, naming the model, kind and object:

::

    $ drift-doctor audit
    [REVERTED] alpha: retire.measure Classes[Class Fill Rate %] (applied 2026-10-22T16:33:22+00:00) — retired measure Classes[Class Fill Rate %] was removed by this fix and is back
    ── audit: checked=1 ok=0 reverted=1 superseded=0 error=0

Publish the review queue
----------------------------

``drift-doctor review --out REVIEW.md`` runs a dry run (nothing is
written) and writes the checklist of everything routed to a person:
blocked retirements, fixes waiting on a precondition, measures on the
wrong or a duplicate host, advisories, and overrides in force. Upload
it as a build artifact so the queue is visible without anyone running
the tool locally:

::

    $ drift-doctor review --out REVIEW.md
    5 review item(s) -> REVIEW.md

The file opens with its own rule: anything that recurs in it is a
missing decision. Encode it once (an override, a ledger revival, an
allowlist entry or a template fix) instead of judging it again on
every run.

Comment on pull requests
----------------------------

Two commands write Markdown for a pull-request comment. Both start
the body with a hidden marker line, so a later run can edit the same
comment in place, and neither fails the build.

**The blast radius of a change.** ``drift-doctor diff`` compares two
``detect --json`` reports, one from the base branch and one from the
pull request:

::

    $ drift-doctor diff --base base.json --head head.json --out blast.md
    blast radius written: blast.md
    15 line(s); 1 of 2 model(s) changed

::

    <!-- drift-doctor:blast-radius -->

    ## Blast radius of this change

    **1 object(s) in 1 model(s).**

    - **measure** `Members[New Members #]` (measure.missing) - resolves drift in 1 model(s)

    | Model | Added | Removed | Net | By kind |
    |---|--:|--:|--:|---|
    | alpha | 0 | 1 | -1 | measure -1 |

    **+0 / -1** actionable item(s) across 1 of 2 model(s).

    _Compared base `b8a1cae22` with head `b8a1cae22`._

Pass ``--fleet fleet.yml`` to also warn when the committed baseline no
longer matches the live template. A report it cannot read exits 2.

**A branch that predates retirements.** ``drift-doctor freshness``
compares the ledger the branch was cut from with the main line's
ledger and names the derived models that still carry an object the
main line has retired since. It always exits 0: the ratchet is the
blocking gate.

::

    $ drift-doctor freshness --base-ledger base-ledger.jsonl --body-file fresh.md --stale-flag-file stale.flag
    base ledger: 0 retirement(s) in force
    head ledger: 1 retirement(s) in force
    unseen: 1 entry
    at risk: measure Visits[Peak Hour Visits] in alpha, bravo
    body written: fresh.md

``--stale-flag-file`` writes ``1`` when something is at risk and an
empty file otherwise, which a later workflow step can test. Without
``--head-ledger`` the head is the fleet's own ledger. In a
pull-request job, extract the base ledger from the merge base with
``git show <merge-base>:.drift-doctor/ledger.jsonl`` (the checkout
needs the history, for example ``fetch-depth: 0`` on
``actions/checkout``). If the merge base has no ledger yet, pass an
empty file: a missing ``--base-ledger`` file is a usage error (exit 2).

GitHub Actions example
--------------------------

The fleet repository holds ``fleet.yml``, the models and the state
directory at its root. The job installs the release it was tested with:

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
          - run: pip install "git+https://github.com/C-Kapsalis/tmdl-drift-doctor@v1.2.1"
          - name: Detect drift (report only)
            run: drift-doctor detect --json > drift.json || true
          - name: Ratchet gate
            run: drift-doctor ratchet check --from-json drift.json
          - name: Audit applied fixes
            run: drift-doctor audit
          - name: Review queue
            if: always()
            run: drift-doctor review --out REVIEW.md
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
instead. If detection hit a parse error, the report's ``errors`` list
is not empty and ``ratchet check`` refuses it with exit 2.

.. warning::

   On a Windows runner, or on a Windows workstation, save the report as
   plain UTF-8 or ASCII. Windows PowerShell 5.1 writes a ``>`` redirect
   as UTF-16, and ``Out-File -Encoding utf8`` adds a byte-order mark;
   ``ratchet`` and ``diff`` cannot read either file. The report is
   pure ASCII, so this form works in Windows PowerShell 5.1 and in
   PowerShell 7:

   ::

       drift-doctor detect --json | Out-File -Encoding ascii drift.json

Policy choices
-----------------

**Warn-only versus gate.** Drift is often expected backlog. The ratchet
is the middle ground: backlog may stay, it may not grow. A stricter
option is a zero-drift ``detect`` gate on pull requests that touch the
template, since those are the ones that create new drift. Put it in a
second workflow with a path filter:

::

    name: template-gate
    on:
      pull_request:
        paths:
          - "template/**"

    jobs:
      zero-drift:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: "3.12"
          - run: pip install "git+https://github.com/C-Kapsalis/tmdl-drift-doctor@v1.2.1"
          - run: drift-doctor detect

**Never remediate in CI.** ``remediate`` belongs in a maintainer's
working tree, where the diffs get reviewed and committed deliberately.
A CI job has no terminal, so a bare ``remediate`` in a job applies
**nothing** and says so::

    note: stdin is not a terminal, so questions are disabled and every item is treated as 'no' (non-interactive). Pass --yes with --kind to apply batch-safe kinds.

If you want automated fix-up pull requests, run ``remediate --dry-run``
in CI, post the diff for review, and keep the actual write on a
person's machine. A job that does write must name the kinds and say
that it means it:

::

    drift-doctor remediate --yes --kind measure.missing

It then applies only the kinds that are safe without a person
(:doc:`../reference/drift-kinds-and-ledger` lists them) and never a
deletion; a deletion needs a yes on a terminal, or ``--sync`` together
with ``--confirm-deletions``.

**Scoped checks.** ``--model`` and ``--kind`` narrow ``detect``, for
example a nightly job that only watches retirements:

::

    drift-doctor detect --kind retire --json > retirements.json

A scoped report is fine to read, but never feed a ``--kind``-filtered
report to the ratchet; it is refused:

::

    $ drift-doctor ratchet check --from-json retirements.json
    ERROR: the report is category-filtered (--kind 'retire'); floors are never compared with or written from a filtered count

A ``--model``-scoped report is accepted: ``check`` compares only its
models, and ``tighten`` lowers only their floors and carries the other
floors forward unchanged.
