Run in CI
=========

Goal: make drift a build signal. Every push tells you whether the fleet
still matches the template, without CI ever mutating a model.

The contract
---------------

``drift-doctor detect`` is read-only and exits:

- ``0``: no findings, or only advisories (``extra.*``),
- ``1``: remediable drift exists,
- non-zero with a stale message: the template changed without a
  recapture.

That last case is a feature in CI: a pull request that edits the
template but forgets ``drift-doctor capture`` fails loudly instead of
producing wrong findings.

GitHub Actions example
--------------------------

::

    name: drift-gate
    on: [push, pull_request]

    jobs:
      detect:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: "3.12"
          - run: pip install ./tools/tmdl-drift-doctor
          - name: Detect drift (read-only)
            run: drift-doctor detect --fleet fleet.yml --json > drift.json
          - name: Upload findings
            if: always()
            uses: actions/upload-artifact@v4
            with:
              name: drift-findings
              path: drift.json

What to commit
------------------

Commit the state directory alongside the models:

- ``.drift-doctor/baseline.json``: CI needs the committed template
  truth; capturing inside CI would compare the template against
  itself.
- ``.drift-doctor/ledger.jsonl``: retirements and revivals are shared
  fleet state, not per-machine caches.

Policy choices
-----------------

**Warn-only versus gate.** Drift is often expected backlog. A pragmatic
middle ground: run ``detect`` warn-only on the fleet, but make it a
hard gate on pull requests that touch the template, since those are the
ones that create new drift:

::

          - name: Gate template PRs
            if: contains(github.event.pull_request.changed_files, 'template/')
            run: drift-doctor detect --fleet fleet.yml

**Never remediate in CI.** ``remediate`` belongs in a maintainer's
working tree, where the diffs get reviewed and committed deliberately.
If you want automated fix-up pull requests, run ``remediate --dry-run``
in CI, post the diff for review, and keep the actual write on a
human's machine.

**Scoped checks.** ``--model`` and ``--kind`` narrow the run, for
example a nightly job that only watches retirements:

::

    $ drift-doctor detect --kind retire. --json
