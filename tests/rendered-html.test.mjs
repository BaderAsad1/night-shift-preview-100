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
  assert.match(html, /PRODUCTION TRAITS/);
  assert.match(html, /BACKGROUND OBJECTS/);
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
  const [oneBitFiles, studioFiles, docsStudioFiles, studioManifestText, docsHtml, docsJs] = await Promise.all([
    readdir(oneBitRoot),
    readdir(studioRoot),
    readdir(docsStudioRoot),
    readFile(new URL("manifest.json", studioRoot), "utf8"),
    readFile(new URL("index.html", docsRoot), "utf8"),
    readFile(new URL("app.js", docsRoot), "utf8"),
  ]);
  const studioManifest = JSON.parse(studioManifestText);
  assert.equal(oneBitFiles.filter((file) => /^\d{3}\.png$/.test(file)).length, 100);
  assert.equal(studioFiles.filter((file) => /^\d{3}\.png$/.test(file)).length, 100);
  assert.equal(docsStudioFiles.filter((file) => /^\d{3}\.png$/.test(file)).length, 100);
  assert.equal(studioManifest.renderCount, 100);
  assert.equal(studioManifest.traitCount, 128);
  assert.equal(studioManifest.uniqueDnaCount, 100);
  assert.equal(studioManifest.uniqueRenderCount, 100);
  assert.equal(studioManifest.verifiedUniqueDnaCapacity, 6666);
  assert.equal(studioManifest.verifiedUniqueRenderCapacity, 6666);
  assert.equal(new Set(studioManifest.characters.map(character => character.id)).size, 100);
  assert.equal(new Set(studioManifest.characters.map(character => JSON.stringify(character.dna))).size, 100);
  assert.equal(studioManifest.characters.every(character => character.dna.length === 6), true);
  assert.equal(studioManifest.palette.traitYellow, "#fdf423");
  assert.equal(studioManifest.compatibilityRules.some(rule => /No background-object category exists/.test(rule)), true);
  const traitNames = studioManifest.traits.map(trait => trait.name.toLowerCase());
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
  const categories = ["base", "headwear", "eyes", "mouth", "outfit", "accessory"];
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
  const codePattern = /^(BA|HW|EY|MO|OF|AC)\d{2}\.png$/;
  assert.deepEqual(publicCategoryFiles.map((files) => files.filter((file) => codePattern.test(file)).length), [8, 30, 24, 16, 30, 20]);
  assert.deepEqual(docsCategoryFiles.map((files) => files.filter((file) => codePattern.test(file)).length), [8, 30, 24, 16, 30, 20]);
  assert.equal(publicFiles.includes("night-shift-128-production-traits.zip"), true);
  assert.equal(docsFiles.includes("night-shift-128-production-traits.zip"), true);
  assert.equal(traitManifest.traitCount, 128);
  assert.equal(traitManifest.traits.length, 128);
  assert.deepEqual(traitManifest.categoryCounts, { Base: 8, Headwear: 30, Eyes: 24, Mouth: 16, Outfit: 30, Accessory: 20 });
  assert.equal(traitManifest.verifiedUniqueRenderCapacity, 6666);
  assert.match(docsHtml, /DOWNLOAD THE/);
  assert.match(docsHtml, /DOWNLOAD ALL 128 TRAITS/);
  assert.match(docsJs, /renderTraitDownloads/);
  assert.match(docsJs, /All Production Traits/);
});
