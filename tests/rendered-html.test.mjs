import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("renders the Night Shift preview gallery", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Night Shift Society — Preview 100/);
  assert.match(html, /MEET THE/);
  assert.match(html, /REVIEW THE BATCH/);
  assert.match(html, /SOURCE ARCHETYPES/);
  assert.match(html, /BACKGROUND OBJECTS/);
  assert.match(html, /V2 TRAIT REVIEW/);
});

test("ships the registered V2 review and standard generator test", async () => {
  const reviewRoot = new URL("../public/review/trait-expansion-v2/", import.meta.url);
  const [html, manifestText, generatorManifestText, cards, transparentCards, outputs] = await Promise.all([
    readFile(new URL("index.html", reviewRoot), "utf8"),
    readFile(new URL("manifest.json", reviewRoot), "utf8"),
    readFile(new URL("generator/output/manifest.json", reviewRoot), "utf8"),
    readdir(new URL("cards/hair-headwear/", reviewRoot)),
    readdir(new URL("cards-transparent/hair-headwear/", reviewRoot)),
    readdir(new URL("generator/output/images/", reviewRoot)),
  ]);
  const manifest = JSON.parse(manifestText);
  const generatorManifest = JSON.parse(generatorManifestText);
  assert.match(html, /WEIGHTED LAYER/);
  assert.match(html, /DOWNLOAD GENERATOR LAYERS/);
  assert.equal(manifest.conceptCount, 128);
  assert.equal(manifest.yellowPolicy, "explicit-mask-eyes-and-approved-flames-only");
  assert.equal(manifest.traits.every((trait) => trait.registration.bodyBaselineY === 512), true);
  assert.equal(cards.filter((file) => /^HH\d{2}\.png$/.test(file)).length, 16);
  assert.equal(transparentCards.filter((file) => /^HH\d{2}\.png$/.test(file)).length, 16);
  assert.equal(generatorManifest.hashLipsCompatibleStructure, true);
  assert.equal(generatorManifest.count, 24);
  assert.equal(outputs.filter((file) => /^\d{4}\.png$/.test(file)).length, 24);
});

test("ships 100 unique character records", async () => {
  const root = new URL("../public/characters/", import.meta.url);
  const files = await readdir(root);
  const pngs = files.filter((file) => /^\d{3}\.png$/.test(file));
  const manifest = JSON.parse(await readFile(new URL("manifest.json", root), "utf8"));
  assert.equal(pngs.length, 100);
  assert.equal(manifest.count, 100);
  assert.equal(manifest.characters.length, 100);
  assert.equal(new Set(manifest.characters.map((character) => character.id)).size, 100);
});

test("ships both one-bit comparison sets and static gallery", async () => {
  const oneBitRoot = new URL("../public/characters-one-bit/", import.meta.url);
  const studioRoot = new URL("../public/characters-one-bit-studio/", import.meta.url);
  const docsRoot = new URL("../docs/", import.meta.url);
  const docsStudioRoot = new URL("studio/", docsRoot);
  const traitSourceRoot = new URL("../reference/neon-nocturne-traits/", import.meta.url);
  const [oneBitFiles, studioFiles, docsStudioFiles, traitSourceFiles, studioManifestText, docsHtml, docsJs] = await Promise.all([
    readdir(oneBitRoot),
    readdir(studioRoot),
    readdir(docsStudioRoot),
    readdir(traitSourceRoot),
    readFile(new URL("manifest.json", studioRoot), "utf8"),
    readFile(new URL("index.html", docsRoot), "utf8"),
    readFile(new URL("app.js", docsRoot), "utf8"),
  ]);
  const studioManifest = JSON.parse(studioManifestText);
  assert.equal(oneBitFiles.filter((file) => /^\d{3}\.png$/.test(file)).length, 100);
  assert.equal(studioFiles.filter((file) => /^\d{3}\.png$/.test(file)).length, 100);
  assert.equal(docsStudioFiles.filter((file) => /^\d{3}\.png$/.test(file)).length, 100);
  assert.equal(traitSourceFiles.filter((file) => /^AR\d{2}\.png$/.test(file)).length, 36);
  assert.equal(studioManifest.count, 100);
  assert.equal(new Set(studioManifest.characters.map(character => character.id)).size, 100);
  assert.equal(new Set(studioManifest.characters.map(character => JSON.stringify(character.traits))).size, 36);
  assert.equal(studioManifest.traitLibrary.moduleCount, 36);
  assert.equal(studioManifest.traitLibrary.collectionTarget, 6666);
  assert.equal(studioManifest.traitLibrary.sourceArchetypeCount, 36);
  assert.equal(studioManifest.traitLibrary.palette.traitYellow, "#fdf423");
  assert.deepEqual(studioManifest.traitLibrary.rendering.normalization, {
    eyeSpan: 160,
    bodyBaselineY: 1024,
    resampling: "nearest",
  });
  assert.equal(new Set(studioManifest.characters.map(character => character.modules.archetype)).size, 36);
  assert.equal(studioManifest.characters.some(character => "motif" in character.modules || "layout" in character.modules), false);
  assert.equal(studioManifest.traitLibrary.rules.some(rule => /No decorative characters, icons, animals, objects, or motifs/.test(rule)), true);
  const traitNames = studioManifest.characters.flatMap(character => character.traits.map(trait => trait.name.toLowerCase()));
  assert.equal(traitNames.some(name => /cross|crucifix|religious|pentagram/.test(name)), false);
  assert.equal(traitNames.some(name => /grid|chart|scan line|checker|waveform|skyline/.test(name)), false);
  assert.match(docsHtml, /SELECT RENDER STYLE/);
  assert.match(docsJs, /1-BIT BLACK/);
  assert.match(docsJs, /NEON NOCTURNE/);
  assert.match(docsJs, /one-bit/);
  assert.match(docsJs, /folder: "studio"/);
});

test("ships the transparent source trait download library", async () => {
  const publicTraitsRoot = new URL("../public/traits/", import.meta.url);
  const docsTraitsRoot = new URL("../docs/traits/", import.meta.url);
  const docsRoot = new URL("../docs/", import.meta.url);
  const categories = ["headwear", "eyes", "outfits", "masters"];
  const [publicFiles, docsFiles, docsHtml, docsJs, traitManifestText] = await Promise.all([
    readdir(publicTraitsRoot),
    readdir(docsTraitsRoot),
    readFile(new URL("index.html", docsRoot), "utf8"),
    readFile(new URL("app.js", docsRoot), "utf8"),
    readFile(new URL("manifest.json", publicTraitsRoot), "utf8"),
  ]);
  const traitManifest = JSON.parse(traitManifestText);
  const publicCategoryFiles = await Promise.all(categories.map((category) => readdir(new URL(`${category}/`, publicTraitsRoot))));
  const docsCategoryFiles = await Promise.all(categories.map((category) => readdir(new URL(`${category}/`, docsTraitsRoot))));
  assert.deepEqual(publicCategoryFiles.map((files) => files.filter((file) => /^(SH|EY|OF|AR)\d{2}\.png$/.test(file)).length), [36, 36, 36, 36]);
  assert.deepEqual(docsCategoryFiles.map((files) => files.filter((file) => /^(SH|EY|OF|AR)\d{2}\.png$/.test(file)).length), [36, 36, 36, 36]);
  assert.equal(publicFiles.includes("night-shift-108-component-traits-transparent.zip"), true);
  assert.equal(docsFiles.includes("night-shift-144-trait-library-transparent.zip"), true);
  assert.equal(traitManifest.componentTraitCount, 108);
  assert.equal(traitManifest.masterCount, 36);
  assert.equal(traitManifest.totalFileCount, 144);
  assert.equal(traitManifest.traits.length, 144);
  assert.equal(traitManifest.traits.filter((trait) => trait.category !== "Master Archetype").length, 108);
  assert.match(docsHtml, /DOWNLOAD THE/);
  assert.match(docsHtml, /DOWNLOAD ALL 108 TRAITS/);
  assert.match(docsJs, /renderTraitDownloads/);
  assert.match(docsJs, /Component Traits/);
});
