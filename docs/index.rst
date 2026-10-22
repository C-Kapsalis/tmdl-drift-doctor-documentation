tmdl-drift-doctor
==================

Drift detection and remediation for a fleet of TMDL-format Power BI
semantic models derived from one template. You maintain one "golden"
model and a copy per client; ``tmdl-drift-doctor`` captures a baseline
of the template, detects typed drift findings in every derived model,
and cascades template truth back out through an auditable,
allowlist-gated pipeline. Deletions need a second opt-in, every applied
fix lands in an append-only ledger, and ``--dry-run`` shows the exact
diffs before anything is written.

``remediate`` confirms every fix with a question, so a run without a
terminal (a script, a pipe, a CI job) writes nothing at all. From a
script, name the kinds you mean and pass ``--yes``; see
:doc:`reference/cli-and-configuration`.

This documentation describes ``drift-doctor`` 1.2.1. Start with
:doc:`tutorials/getting-started`, then use the how-to guides for the
recurring jobs and the reference pages to look things up.

Audience
-----------

This is written for BI agencies and platform teams who already run a
template-and-fleet setup, or are about to: one governed semantic model,
cloned or forked per client, tenant or region. It assumes you are
comfortable with Power BI's TMDL format and can read a ``fleet.yml``
and a raw TMDL block without a primer. Commands are shown for bash and
for PowerShell where the two differ; the package is
``tmdl-drift-doctor`` and the command it installs is ``drift-doctor``.

Why this matters
--------------------

`tmdl-preflight <https://tmdl-preflight-documentation.readthedocs.io/en/latest/index.html>`_
keeps one model honest against a rule catalog; ``tmdl-drift-doctor``
keeps a whole fleet of models honest against each other. The two
problems compound: a template that passes preflight still drifts from
its derived copies the moment someone edits a client model directly,
and a fleet with no drift tooling turns "does every client have the
latest KPI" into an afternoon of diffing folders by hand. Capture,
detect, and remediate turn that afternoon into three commands, with a
ledger that answers "why did this change" months later.

.. toctree::
   :maxdepth: 1

   tutorials/getting-started
   how-to/index
   reference/cli-and-configuration
   reference/drift-kinds-and-ledger
   contributing
