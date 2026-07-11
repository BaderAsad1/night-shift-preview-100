const manifest = window.TRAIT_REVIEW_MANIFEST;
const storageKey = "neon-nocturne-v2-decisions";
const decisions = JSON.parse(localStorage.getItem(storageKey) || "{}");
const labels = {
  all: "ALL 128",
  "hair-headwear": "HAIR + HEADWEAR",
  eyes: "EYES",
  eyewear: "EYEWEAR",
  mouths: "MOUTHS",
  outfits: "OUTFITS",
  neck: "NECK + CHEST",
  rare: "RARE",
  "face-details": "FACE DETAILS",
};
let category = "all";

const grid = document.querySelector("#trait-grid");
const filters = document.querySelector("#filters");
const template = document.querySelector("#trait-template");

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

function renderCards() {
  const traits = category === "all" ? manifest.traits : manifest.traits.filter(trait => trait.category === category);
  grid.replaceChildren(...traits.map(trait => {
    const card = template.content.firstElementChild.cloneNode(true);
    const image = card.querySelector("img");
    image.src = trait.card;
    image.alt = `${trait.code} ${trait.name} concept preview`;
    card.querySelector(".trait-copy code").textContent = trait.code;
    card.querySelector(".trait-copy strong").textContent = trait.name;
    const download = card.querySelector(".trait-download");
    download.href = trait.transparentPreview;
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
    decisions: manifest.traits.map(trait => ({ code: trait.code, name: trait.name, decision: decisions[trait.code] || "pending" })),
  };
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  link.download = "neon-nocturne-v2-decisions.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

renderFilters();
renderCards();
renderGeneratorTest();
updateCounts();
