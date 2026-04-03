# rac-us-co

Colorado benefit-program RAC encodings, starting with the Colorado Works Program in
`9 CCR 2503-6` and its immediate Colorado statute companions.

This repo is for Colorado non-statutory benefit rules such as regulations, manuals,
and administrative guidance. The first slice is sourced from the official Colorado
Works Program PDF published by the Colorado Secretary of State.

## Current scope

- full-source snapshot for `9 CCR 2503-6`
- `akomize`-generated Akoma Ntoso skeleton for that PDF
- exact clause slices for the first encoded provisions
- Colorado statute companion definitions under `C.R.S. § 26-2-703`
- initial RAC leaves for:
  - SSI exclusion from the assistance unit
  - pregnancy allowance
  - gross-income need-standard test
  - basic cash-assistance grant calculation for an eligible assistance unit
  - assistance-unit definition
  - basic-cash-assistance-grant definition

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
├── statute/
│   └── crs/
│       └── 26-2-703/
│           ├── 2.5.rac
│           └── 3.rac
├── sources/
│   ├── official/9-CCR-2503-6/2026-04-02/
│   │   ├── source.pdf
│   │   ├── outline.json
│   │   └── source.akn.xml
│   ├── official/statute/crs/26-2-703/2026-04-02/source.html
│   └── slices/
│       ├── 9-CCR-2503-6/
│       └── statute/crs/26-2-703/
├── scripts/
│   └── sync_atlas.py
└── waves/
    ├── 2026-04-02-wave1/manifest.json
    └── 2026-04-02-wave2/manifest.json
```

## Commands

```bash
# Validate schema and imports
cd /Users/maxghenis/TheAxiomFoundation/rac
uv run python -m rac.validate all /Users/maxghenis/TheAxiomFoundation/rac-us-co

# Run inline tests
cd /Users/maxghenis/TheAxiomFoundation/rac
uv run python -m rac.test_runner /Users/maxghenis/TheAxiomFoundation/rac-us-co -v

# Sync Colorado rows into Atlas/Supabase
cd /Users/maxghenis/TheAxiomFoundation/rac-us-co
python3 scripts/sync_atlas.py
```

## Notes

- The current `from ...` dates are conservative.
  - Where `akomize` recovered a rule-specific effective date from editor's notes, the
    RAC leaf uses that date.
  - Otherwise the leaf is anchored to the current-text source snapshot retrieved on
    `2026-04-02`.
- This is intentionally a narrow seed, not a full Colorado Works corpus yet.
- The first statute companions live under `statute/crs/26-2-703/` so the manual and
  statute sides can grow together.
