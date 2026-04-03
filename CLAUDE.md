# rac-us-co

Colorado benefit-program encodings live here.

## Scope

- Colorado administrative regulations, manuals, and guidance
- first source: `9 CCR 2503-6` Colorado Works Program
- keep statute companions separate under `statute/` when added later

## Layout

```text
rac-us-co/
├── regulation/        # Colorado regulations and rule manuals
├── statute/           # Colorado statutes when needed for imports
├── sources/
│   ├── official/      # full PDF + AKN snapshots
│   └── slices/        # exact clause text for atomic leaves
└── waves/             # wave provenance manifests
```

## Local commands

```bash
cd /Users/maxghenis/TheAxiomFoundation/rac
uv run python -m rac.validate all /Users/maxghenis/TheAxiomFoundation/rac-us-co/regulation
uv run python -m rac.test_runner /Users/maxghenis/TheAxiomFoundation/rac-us-co/regulation -v
```

## Encoding policy

- Prefer the most atomic rule slice possible.
- If a leaf is derived from a larger manual subsection, keep the exact excerpt in
  `sources/slices/`.
- Do not invent convenience scalars inside formulas; every substantive number should
  be its own variable.
- If a rule depends on statute text, add or import the statute companion instead of
  paraphrasing it locally.
