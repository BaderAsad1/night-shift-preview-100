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
  assert.match(html, /RELIGIOUS REFERENCES/);
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
  assert.equal(studioManifest.count, 100);
  assert.equal(new Set(studioManifest.characters.map(character => character.id)).size, 100);
  assert.equal(new Set(studioManifest.characters.map(character => JSON.stringify(character.traits))).size, 100);
  const traitNames = studioManifest.characters.flatMap(character => character.traits.map(trait => trait.name.toLowerCase()));
  assert.equal(traitNames.some(name => /cross|crucifix|religious|pentagram/.test(name)), false);
  assert.match(docsHtml, /SELECT RENDER STYLE/);
  assert.match(docsJs, /1-BIT BLACK/);
  assert.match(docsJs, /NEON NOCTURNE/);
  assert.match(docsJs, /one-bit/);
  assert.match(docsJs, /folder: "studio"/);
});
