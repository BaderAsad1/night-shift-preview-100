"use client";

import { useEffect, useMemo, useState } from "react";

type Trait = { category: string; code: string; name: string };
type Character = {
  id: number;
  name: string;
  house: string;
  accent: string;
  motto: string;
  image: string;
  traits: Trait[];
};
type House = { name: string; accent: string; motto: string };
type Manifest = {
  collection: string;
  status: string;
  count: number;
  traitConcepts: number;
  houses: House[];
  characters: Character[];
};
type TraitSource = {
  category: string;
  code: string;
  name: string;
  file: string;
  rarity: string;
};

function PixelMark() {
  return (
    <span className="pixel-mark" aria-hidden="true">
      <i /><i /><i /><i /><i /><i />
    </span>
  );
}

export function Gallery({ manifest, traitSources }: { manifest: Manifest; traitSources: TraitSource[] }) {
  const [house, setHouse] = useState("All Houses");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Character | null>(null);
  const [copied, setCopied] = useState(false);
  const [traitCategory, setTraitCategory] = useState("All Production Traits");

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return manifest.characters.filter((character) => {
      if (house !== "All Houses" && character.house !== house) return false;
      if (!q) return true;
      const haystack = [
        character.name,
        character.house,
        character.id.toString(),
        ...character.traits.flatMap((trait) => [trait.name, trait.code, trait.category]),
      ].join(" ").toLowerCase();
      return haystack.includes(q);
    });
  }, [house, manifest.characters, query]);

  const downloadableTraits = useMemo(() => (
    traitCategory === "All Production Traits"
      ? traitSources
      : traitSources.filter((trait) => trait.category === traitCategory)
  ), [traitCategory, traitSources]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && setSelected(null);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);

  async function copyReview(character: Character) {
    const traits = character.traits.map((trait) => `${trait.category}: ${trait.name}`).join("; ");
    await navigator.clipboard.writeText(`${character.name} — ${character.house}\n${traits}\nReview: `);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Night Shift Society home">
          <PixelMark />
          <span>NIGHT SHIFT SOCIETY</span>
        </a>
        <div className="preview-pill"><span /> TEAM PREVIEW</div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow">BATCH 01 / CONCEPT REVIEW</div>
          <h1>MEET THE<br /><em>PREVIEW 100</em></h1>
          <p>
            One hundred 8-bit night creatures assembled from the expanded trait library.
            Explore the Houses, inspect every layer, and flag the combinations worth taking into production.
          </p>
          <a className="primary-action" href="#collection">ENTER THE ARCHIVE <span>↓</span></a>
        </div>
        <div className="hero-stack" aria-hidden="true">
          {[7, 18, 1].map((id, index) => {
            const character = manifest.characters[id - 1];
            return (
              <div className={`stack-card stack-${index + 1}`} key={id} style={{ "--accent": character.accent } as React.CSSProperties}>
                <img src={character.image} alt="" />
                <span>#{id.toString().padStart(3, "0")}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="metrics" aria-label="Collection overview">
        <div><strong>100</strong><span>CHARACTERS</span></div>
        <div><strong>128</strong><span>PRODUCTION TRAITS</span></div>
        <div><strong>6</strong><span>NIGHT HOUSES</span></div>
        <div><strong>0</strong><span>BACKGROUND OBJECTS</span></div>
      </section>

      <section className="collection" id="collection">
        <div className="section-heading">
          <div>
            <span className="kicker">THE WORKING ARCHIVE</span>
            <h2>REVIEW THE BATCH</h2>
          </div>
          <p>{visible.length.toString().padStart(3, "0")} / {manifest.count} SHOWN</p>
        </div>

        <div className="controls">
          <div className="filters" aria-label="Filter by House">
            {["All Houses", ...manifest.houses.map((item) => item.name)].map((name) => (
              <button className={house === name ? "active" : ""} key={name} onClick={() => setHouse(name)}>
                {name}
              </button>
            ))}
          </div>
          <label className="search">
            <span>⌕</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search #, trait or House" aria-label="Search characters" />
          </label>
        </div>

        <div className="gallery-grid">
          {visible.map((character) => (
            <button
              className="character-card"
              key={character.id}
              onClick={() => setSelected(character)}
              style={{ "--accent": character.accent } as React.CSSProperties}
              aria-label={`Inspect ${character.name}`}
            >
              <span className="image-well"><img src={character.image} alt={character.name} loading="lazy" /></span>
              <span className="card-meta">
                <span><b>#{character.id.toString().padStart(3, "0")}</b><small>{character.house}</small></span>
                <span className="inspect">↗</span>
              </span>
            </button>
          ))}
        </div>

        {visible.length === 0 && (
          <div className="empty-state">No night creatures match that search.</div>
        )}
      </section>

      <section className="trait-library" id="trait-downloads">
        <div className="trait-library-head">
          <div>
            <span className="kicker">PRODUCTION FILES / TRANSPARENT PNG</span>
            <h2>DOWNLOAD THE<br />TRAIT LIBRARY</h2>
            <p>128 genuine interchangeable production layers across six registered categories: 8 bases, 30 headwear traits, 24 eye treatments, 16 mouths, 30 outfits, and 20 anchored accessories. Every file is a transparent 1024×1024 PNG on the same canonical grid.</p>
          </div>
          <a className="batch-download" href="/traits/night-shift-128-production-traits.zip" download>
            <span>DOWNLOAD ALL 128 TRAITS</span><small>ZIP · PRODUCTION LAYERS</small><b>↓</b>
          </a>
        </div>
        <div className="trait-category-bar" aria-label="Filter trait downloads">
          {["All Production Traits", "Base", "Headwear", "Eyes", "Mouth", "Outfit", "Accessory"].map((category) => (
            <button className={traitCategory === category ? "active" : ""} key={category} onClick={() => setTraitCategory(category)}>
              {category} · {category === "All Production Traits" ? traitSources.length : traitSources.filter((trait) => trait.category === category).length}
            </button>
          ))}
        </div>
        <div className="trait-batch-links">
          <a href="/traits/night-shift-base-traits.zip" download>BASES 8 ↓</a>
          <a href="/traits/night-shift-headwear-traits.zip" download>HEADWEAR 30 ↓</a>
          <a href="/traits/night-shift-eyes-traits.zip" download>EYES 24 ↓</a>
          <a href="/traits/night-shift-mouth-traits.zip" download>MOUTHS 16 ↓</a>
          <a href="/traits/night-shift-outfit-traits.zip" download>OUTFITS 30 ↓</a>
          <a href="/traits/night-shift-accessory-traits.zip" download>ACCESSORIES 20 ↓</a>
          <a href="/characters-one-bit-studio/night-shift-100-test-renders.zip" download>TEST RENDERS 100 ↓</a>
          <a href="/characters-one-bit-studio/night-shift-100-test-metadata.zip" download>TEST METADATA 100 ↓</a>
        </div>
        <div className="trait-download-grid" aria-label="Transparent trait downloads">
          {downloadableTraits.map((trait) => (
            <article className="trait-download-card" key={trait.code}>
              <div className="trait-preview"><img src={`/${trait.file}`} alt={`${trait.name} transparent ${trait.category} trait`} loading="lazy" /></div>
              <div className="trait-download-meta">
                <span><code>{trait.code}</code><strong>{trait.name}</strong></span>
                <a href={`/${trait.file}`} download={`${trait.code}.png`} aria-label={`Download ${trait.name} transparent PNG`}>PNG ↓</a>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="review-note">
        <div className="note-number">01</div>
        <div>
          <span className="kicker">WHAT THIS BATCH IS FOR</span>
          <h2>FIND THE SIGNAL.<br />FLAG THE NOISE.</h2>
        </div>
        <p>
          These are composition previews built from the approved concept boards—not final mint-ready artwork.
          Review silhouette, character energy, trait pairings, and House direction. Pixel cleanup and production registration come next.
        </p>
      </section>

      <footer>
        <span>NIGHT SHIFT SOCIETY</span>
        <span>PREVIEW 100 · INTERNAL REVIEW</span>
      </footer>

      {selected && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <section className="detail-modal" role="dialog" aria-modal="true" aria-label={`${selected.name} traits`} onMouseDown={(event) => event.stopPropagation()}>
            <button className="close" onClick={() => setSelected(null)} aria-label="Close">×</button>
            <div className="detail-image" style={{ "--accent": selected.accent } as React.CSSProperties}>
              <img src={selected.image} alt={selected.name} />
              <span>{selected.house}</span>
            </div>
            <div className="detail-copy">
              <span className="kicker">CHARACTER FILE</span>
              <h2>{selected.name}</h2>
              <p className="motto">“{selected.motto}”</p>
              <div className="trait-list">
                {selected.traits.map((trait) => (
                  <div key={`${trait.category}-${trait.code}`}>
                    <span>{trait.category}</span>
                    <strong>{trait.name}</strong>
                    <code>{trait.code}</code>
                  </div>
                ))}
              </div>
              <button className="copy-button" onClick={() => copyReview(selected)}>{copied ? "COPIED" : "COPY REVIEW NOTE"}</button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
