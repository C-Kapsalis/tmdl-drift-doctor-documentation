tmdl-drift-doctor
==================

Drift detection and auto-remediation for fleets of TMDL-format Power BI
semantic models derived from one template. You maintain one template
("golden") model and a copy per client; ``tmdl-drift-doctor`` captures a
baseline of the template, detects typed drift findings in every derived
model, and remediates them through an auditable, allowlist-gated cascade
of template truth back out to the fleet. Deletions require double
opt-in, every applied fix lands in an append-only ledger, and
``--dry-run`` shows the exact diffs first.

The documentation follows the `Diátaxis <https://diataxis.fr/>`_
framework: tutorials teach, how-to guides solve, reference informs,
explanation deepens.

.. toctree::
   :maxdepth: 1

   tutorials/getting-started
   how-to/add-a-model
   how-to/cascade-a-column-retirement
   how-to/recover-from-unwanted-remediation
   how-to/run-in-ci
   reference/cli
   reference/configuration
   reference/drift-kinds
   reference/ledger-format
   explanation/baseline-recapture-discipline
   explanation/allowlist-only-cascading
   explanation/ledger-and-revival
   explanation/safe-tmdl-surgery
   explanation/missing-objects
   explanation/expression-drift
   explanation/property-drift
   explanation/extra-objects
   explanation/object-retirement
   explanation/column-retirement
   explanation/mapping-row-retirement
