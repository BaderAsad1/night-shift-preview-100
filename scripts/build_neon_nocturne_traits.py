#!/usr/bin/env python3
"""Build reusable, normalized Neon Nocturne portrait trait assets."""

from build_neon_nocturne import TRAIT_SOURCE_DIR, build_portrait_trait_sources


if __name__ == "__main__":
    build_portrait_trait_sources(TRAIT_SOURCE_DIR)
    print(f"Built 36 normalized portrait traits in {TRAIT_SOURCE_DIR}")
