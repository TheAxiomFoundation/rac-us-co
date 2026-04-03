# rac-us-co

Colorado benefit-program RAC encodings, starting with the Colorado Works Program in
`9 CCR 2503-6`.

This repo is for Colorado non-statutory benefit rules such as regulations, manuals,
and administrative guidance. The first slice is sourced from the official Colorado
Works Program PDF published by the Colorado Secretary of State.

## Current scope

- full-source snapshot for `9 CCR 2503-6`
- `akomize`-generated Akoma Ntoso skeleton for that PDF
- exact clause slices for the first encoded provisions
- initial RAC leaves for:
  - SSI exclusion from the assistance unit
  - pregnancy allowance
  - gross-income need-standard test
  - basic cash-assistance grant calculation for an eligible assistance unit

## Structure

```text
rac-us-co/
├── regulation/
│   └── 9-CCR-2503-6/
│       ├── 3.604.2/C/3/a.rac
│       └── 3.606.1/
│           ├── G.rac
│           ├── H.rac
│           └── I.rac
├── sources/
│   ├── official/9-CCR-2503-6/2026-04-02/
│   │   ├── source.pdf
│   │   ├── outline.json
│   │   └── source.akn.xml
│   └── slices/9-CCR-2503-6/
└── waves/
    └── 2026-04-02-wave1/manifest.json
```

## Commands

```bash
# Validate schema and imports
cd /Users/maxghenis/TheAxiomFoundation/rac
uv run python -m rac.validate all /Users/maxghenis/TheAxiomFoundation/rac-us-co/regulation

# Run inline tests
cd /Users/maxghenis/TheAxiomFoundation/rac
uv run python -m rac.test_runner /Users/maxghenis/TheAxiomFoundation/rac-us-co/regulation -v
```

## Notes

- The current `from ...` dates are conservative.
  - Where `akomize` recovered a rule-specific effective date from editor's notes, the
    RAC leaf uses that date.
  - Otherwise the leaf is anchored to the current-text source snapshot retrieved on
    `2026-04-02`.
- This is intentionally a narrow seed, not a full Colorado Works corpus yet.
- The next natural step is to add the related Colorado statutes and then expand deeper
  into `3.606` and the assistance-unit rules in `3.604.2`.
