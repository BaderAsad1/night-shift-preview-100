const manifest = window.TRAIT_REVIEW_MANIFEST;
const layerManifest = window.ISOLATED_TRAIT_MANIFEST;
const storageKey = "neon-nocturne-v2-decisions";
const decisions = JSON.parse(localStorage.getItem(storageKey) || "{}");
const labels = {
  all: "ALL 129 LAYERS",
  "00-base": "BASE",
  "01-hair-headwear": "HAIR + HEADWEAR",
  "02-eyes": "EYES",
  "03-eyewear": "EYEWEAR",
  "04-mouths": "MOUTHS",
  "05-clothing": "CLOTHING",
  "06-neck-accessories": "NECK ACCESSORIES",
  "07-face-details": "FACE DETAILS",
  "08-rare-overrides": "RARE OVERRIDES",
};
let category = "all";
const viewModes = {};

const grid = document.querySelector("#trait-grid");
const filters = document.querySelector("#filters");
const template = document.querySelector("#trait-template");
const layerByCode = new Map(layerManifest.layers.map(layer => [layer.code, layer]));
const reviewItems = layerManifest.layers.map(layer => ({
  code: layer.code,
  name: layer.name,
  category: layer.category,
}));

function save() {
  localStorage.setItem(storageKey, JSON.stringify(decisions));
  updateCounts();
}

function updateCounts() {
  const values = Object.values(decisions);
  document.querySelector("#approved-count").textContent = values.filter(value => value === "approve").length;
  document.querySelector("#revise-count").textContent = values.filter(value => value === "revise").length;
  document.querySelector("#rejected-count").textContent = values.filter(value => value === "reject").length;
}

function renderFilters() {
  filters.replaceChildren(...Object.entries(labels).map(([value, label]) => {
    const button = document.createElement("button");
    button.textContent = label;
    button.className = category === value ? "active" : "";
    button.addEventListener("click", () => { category = value; renderFilters(); renderCards(); });
    return button;
  }));
}

function renderBatchActions() {
  const actions = document.querySelector("#batch-actions");
  const downloads = [
    ["ALL 129 FILES", "isolated-layers/neon-nocturne-all-129-generator-layers.zip"],
    ...layerManifest.categories.map(value => [labels[value], `isolated-layers/neon-nocturne-${value}-layers.zip`]),
  ];
  actions.replaceChildren(...downloads.map(([label, href], index) => {
    const link = document.createElement("a");
    link.href = href;
    link.download = "";
    link.textContent = `${label} ↓`;
    if (index === 0) link.className = "primary";
    return link;
  }));
}

function renderCards() {
  const traits = category === "all" ? reviewItems : reviewItems.filter(trait => trait.category === category);
  grid.replaceChildren(...traits.map(trait => {
    const layer = layerByCode.get(trait.code);
    const card = template.content.firstElementChild.cloneNode(true);
    const image = card.querySelector("img");
    const imageWrap = card.querySelector(".image-wrap");
    const toggle = card.querySelector(".view-toggle");
    const showReference = viewModes[trait.code] === "reference";
    image.src = showReference ? layer.referenceCard : layer.layer;
    image.alt = `${trait.code} ${trait.name} ${showReference ? "on-character reference" : "isolated transparent layer"}`;
    imageWrap.classList.toggle("checker", !showReference);
    imageWrap.classList.toggle("reference", showReference);
    toggle.textContent = showReference ? "ISOLATED" : "REFERENCE";
    toggle.setAttribute("aria-label", `Show ${showReference ? "isolated layer" : "on-character reference"} for ${trait.code} ${trait.name}`);
    toggle.addEventListener("click", () => {
      viewModes[trait.code] = showReference ? "isolated" : "reference";
      renderCards();
    });
    card.querySelector(".trait-copy code").textContent = trait.code;
    card.querySelector(".trait-copy strong").textContent = trait.name;
    const download = card.querySelector(".trait-download");
    download.href = layer.layer;
    download.download = `${trait.code}.png`;
    download.setAttribute("aria-label", `Download ${trait.code} ${trait.name} transparent PNG`);
    card.querySelectorAll("[data-decision]").forEach(button => {
      button.classList.toggle("active", decisions[trait.code] === button.dataset.decision);
      button.addEventListener("click", () => {
        decisions[trait.code] = decisions[trait.code] === button.dataset.decision ? undefined : button.dataset.decision;
        if (!decisions[trait.code]) delete decisions[trait.code];
        save();
        renderCards();
      });
    });
    return card;
  }));
}

function renderGeneratorTest() {
  const test = window.NFT_GENERATOR_TEST;
  const generatorGrid = document.querySelector("#generator-grid");
  if (!test || !generatorGrid) return;
  generatorGrid.replaceChildren(...test.outputs.map(output => {
    const article = document.createElement("article");
    article.className = "generator-card";
    const image = document.createElement("img");
    image.src = `generator/output/${output.localImage}`;
    image.alt = output.name;
    image.loading = "lazy";
    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `#${String(output.edition).padStart(4, "0")}`;
    const trait = document.createElement("span");
    trait.textContent = output.attributes.map(attribute => `${attribute.code} · ${attribute.value}`).join(" / ");
    const metadata = document.createElement("a");
    metadata.href = `generator/output/${output.metadataFile}`;
    metadata.download = "";
    metadata.textContent = "JSON ↓";
    copy.append(title, trait, metadata);
    article.append(image, copy);
    return article;
  }));
}

document.querySelector("#export-decisions").addEventListener("click", () => {
  const payload = {
    collection: manifest.collection,
    edition: manifest.edition,
    exportedAt: new Date().toISOString(),
    decisions: reviewItems.map(trait => ({ code: trait.code, name: trait.name, category: trait.category, decision: decisions[trait.code] || "pending" })),
  };
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  link.download = "neon-nocturne-v2-decisions.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

renderFilters();
renderBatchActions();
renderCards();
renderGeneratorTest();
updateCounts();
