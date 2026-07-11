# Neon Nocturne layered generator test

This folder follows the conventional HashLips model:

- `layers/` contains ordered full-canvas transparent PNG layers.
- A filename ending in `#number` declares its rarity weight.
- `config.json` fixes layer order, edition size, seed, background, and base URI.
- `output/images/` contains deterministic composites.
- `output/json/` and `output/_metadata.json` contain mint-style metadata and DNA.

Run from the project root:

```text
python3 scripts/prepare_standard_nft_generator.py
python3 scripts/generate_layered_nfts.py
python3 scripts/audit_layered_nft_generator.py
```

## Layer structure

The normal generator uses eight ordered folders: clothing, locked base,
hair/headwear, eyes, mouths, optional eyewear, optional neck accessories, and
optional face details. Every input is a separate 1028×1028 transparent PNG.
Rare overrides remain in the review library as a separate full-character set
and are intentionally excluded from mixed normal combinations.
