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

## Current limitation

The 128 V2 review images are complete-character concepts, not isolated
mix-and-match trait layers. They are packaged as one `Complete Character` layer
to prove the generator, weighting, uniqueness, metadata, and QA pipeline without
producing false composites. A 6,666-piece collection requires approved isolated
layers for body, outfit, eyes, mouth, hair/headwear, accessories, and rare traits
on the same registered canvas.
