"use client";

import { useEffect, useMemo, useState } from "react";

type RecordItem = {
  edition: number;
  source_master: number;
  eyes: string;
  expression: string;
  image_sha256: string;
  dna: string;
  status: string;
};

type Manifest = {
  requested: number;
  generated: number;
  curated_masters: number;
  unique_image_hashes: number;
  mechanically_rejected: number;
  records: RecordItem[];
};

type Audit = {
  accepted_images: number;
  metadata_files: number;
  unique_dna: number;
  unique_image_hashes: number;
  records_passed: number;
  records_failed: number;
  passed: boolean;
};

type Metadata = {
  name: string;
  description: string;
  dna: string;
  attributes: Array<{ trait_type: string; value: string }>;
};

const ROOT = "/review/launch-candidate-666";

export function LaunchGallery({ manifest, audit }: { manifest: Manifest; audit: Audit }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<RecordItem | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return manifest.records;
    return manifest.records.filter((item) => {
      const number = item.edition.toString().padStart(3, "0");
      return [number, item.edition, item.source_master, item.eyes, item.expression]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [manifest.records, query]);

  useEffect(() => {
    if (!selected) {
      setMetadata(null);
      return;
    }
    const number = selected.edition.toString().padStart(3, "0");
    fetch(`${ROOT}/metadata/${number}.json`).then((response) => response.json()).then(setMetadata);
  }, [selected]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && setSelected(null);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);

  const heroEditions = [1, 15, 24];

  return (
    <main className="launch-shell">
      <header className="launch-topbar">
        <a href="#top" className="launch-brand"><span className="launch-dot" />NIGHT SHIFT SOCIETY</a>
        <nav>
          <a href="#collection">666 GALLERY</a>
          <a href={`${ROOT}/contact-sheets/page-1.png`}>QA SHEETS</a>
          <a href="/review/trait-expansion-v2/index.html">TRAIT REVIEW</a>
        </nav>
      </header>

      <section className="launch-hero" id="top">
        <div>
          <span className="launch-kicker">FINAL LAUNCH CANDIDATE / TEAM REVIEW</span>
          <h1>NEON<br /><em>NOCTURNE</em><br />666</h1>
          <p>Six hundred and sixty-six individually rendered 1028×1028 pixel artworks with one-to-one mint metadata, fixed three-quarter direction, exact palette, and a completed collection audit.</p>
          <div className="launch-actions">
            <a href="#collection">REVIEW ALL 666 ↓</a>
            <a className="ghost" href={`${ROOT}/night-shift-666-complete.zip`} download>COMPLETE BATCH ↓</a>
          </div>
        </div>
        <div className="launch-hero-art" aria-hidden="true">
          {heroEditions.map((edition, index) => (
            <figure key={edition} className={`launch-hero-card card-${index + 1}`}>
              <img src={`${ROOT}/images/${edition.toString().padStart(3, "0")}.png`} alt="" />
              <figcaption>#{edition.toString().padStart(3, "0")}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="launch-metrics" aria-label="Collection audit">
        <div><strong>{manifest.generated}</strong><span>ARTWORKS</span></div>
        <div><strong>{audit.metadata_files}</strong><span>METADATA FILES</span></div>
        <div><strong>{audit.unique_dna}</strong><span>UNIQUE DNA</span></div>
        <div><strong>{audit.records_failed}</strong><span>FAILED AUDITS</span></div>
      </section>

      <section className="launch-downloads">
        <div><span className="launch-kicker">DELIVERY PACKAGES</span><h2>READY FOR THE TEAM</h2></div>
        <div className="launch-download-grid">
          <a href={`${ROOT}/night-shift-666-images.zip`} download><strong>666 IMAGES</strong><small>1028×1028 PNG · ZIP</small><b>↓</b></a>
          <a href={`${ROOT}/night-shift-666-metadata.zip`} download><strong>666 METADATA</strong><small>ONE-TO-ONE JSON · ZIP</small><b>↓</b></a>
          <a href={`${ROOT}/night-shift-666-complete.zip`} download><strong>COMPLETE PACKAGE</strong><small>ART + JSON + QA · ZIP</small><b>↓</b></a>
          <a href={`${ROOT}/qa/final-audit.json`}><strong>AUDIT REPORT</strong><small>666 / 666 PASSED · JSON</small><b>↗</b></a>
        </div>
      </section>

      <section className="launch-gallery-section" id="collection">
        <div className="launch-section-head">
          <div><span className="launch-kicker">THE COMPLETE COLLECTION</span><h2>INSPECT EVERY EDITION</h2></div>
          <label className="launch-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search #, eye or expression" aria-label="Search the collection" /></label>
        </div>
        <div className="launch-count">{visible.length} / 666 SHOWN</div>
        <div className="launch-grid">
          {visible.map((item) => {
            const number = item.edition.toString().padStart(3, "0");
            return (
              <button key={item.edition} className="launch-card" onClick={() => setSelected(item)} aria-label={`Inspect edition ${number}`}>
                <img src={`${ROOT}/images/${number}.png`} alt={`Neon Nocturne #${number}`} loading="lazy" />
                <span><strong>#{number}</strong><small>{item.eyes.replaceAll("-", " ")}</small><b>↗</b></span>
              </button>
            );
          })}
        </div>
      </section>

      <footer className="launch-footer"><span>NIGHT SHIFT SOCIETY</span><span>666 LAUNCH REVIEW · AUDIT PASS</span></footer>

      {selected && (
        <div className="launch-modal-backdrop" onMouseDown={() => setSelected(null)}>
          <section className="launch-modal" role="dialog" aria-modal="true" aria-label={`Edition ${selected.edition}`} onMouseDown={(event) => event.stopPropagation()}>
            <button className="launch-close" onClick={() => setSelected(null)} aria-label="Close">×</button>
            <img src={`${ROOT}/images/${selected.edition.toString().padStart(3, "0")}.png`} alt={metadata?.name ?? "Selected edition"} />
            <div className="launch-modal-copy">
              <span className="launch-kicker">INDIVIDUAL EDITION</span>
              <h2>{metadata?.name ?? `Neon Nocturne #${selected.edition.toString().padStart(3, "0")}`}</h2>
              <div className="launch-traits">
                {metadata?.attributes.map((trait) => <div key={trait.trait_type}><span>{trait.trait_type}</span><strong>{trait.value}</strong></div>)}
              </div>
              <div className="launch-modal-actions">
                <a href={`${ROOT}/images/${selected.edition.toString().padStart(3, "0")}.png`} download>IMAGE PNG ↓</a>
                <a href={`${ROOT}/metadata/${selected.edition.toString().padStart(3, "0")}.json`} download>METADATA JSON ↓</a>
              </div>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
