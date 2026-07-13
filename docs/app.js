const REPO = "https://raw.githubusercontent.com/BaderAsad1/night-shift-preview-100/main";
const ROOT = `${REPO}/public/review/launch-candidate-666`;
const RELEASES = `${REPO}/downloads`;
const pad = value => String(value).padStart(3, "0");

const links = {
  "complete-download": `${RELEASES}/night-shift-666-complete.zip`,
  "images-download": `${RELEASES}/night-shift-666-images.zip`,
  "metadata-download": `${RELEASES}/night-shift-666-metadata.zip`,
  "all-download": `${RELEASES}/night-shift-666-complete.zip`,
  "audit-download": `${ROOT}/qa/final-audit.json`,
  "qa-link": `${ROOT}/qa/final-audit.json`,
};
Object.entries(links).forEach(([id, href]) => document.getElementById(id).href = href);
[["hero-1", 1], ["hero-2", 15], ["hero-3", 24]].forEach(([id, edition]) => document.getElementById(id).src = `${ROOT}/images/${pad(edition)}.png`);

const gallery = document.getElementById("gallery");
const count = document.getElementById("count");
const search = document.getElementById("search");
const modal = document.getElementById("modal");
let records = [];

function render(items) {
  count.textContent = `${items.length} / 666 SHOWN`;
  gallery.replaceChildren(...items.map(item => {
    const number = pad(item.edition);
    const card = document.createElement("button");
    card.className = "card";
    card.setAttribute("aria-label", `Inspect edition ${number}`);
    card.innerHTML = `<img src="${ROOT}/images/${number}.png" alt="Neon Nocturne #${number}" loading="lazy"><span><strong>#${number}</strong><small>${item.eyes.replaceAll("-", " ")}</small><b>↗</b></span>`;
    card.addEventListener("click", () => inspect(number));
    return card;
  }));
}

async function inspect(number) {
  const metadataUrl = `${ROOT}/metadata/${number}.json`;
  const metadata = await fetch(metadataUrl).then(response => response.json());
  document.getElementById("modal-title").textContent = metadata.name;
  document.getElementById("modal-image").src = `${ROOT}/images/${number}.png`;
  document.getElementById("image-link").href = `${ROOT}/images/${number}.png`;
  document.getElementById("metadata-link").href = metadataUrl;
  document.getElementById("traits").innerHTML = metadata.attributes.map(item => `<div><span>${item.trait_type}</span><strong>${item.value}</strong></div>`).join("");
  modal.hidden = false;
}

document.getElementById("close").addEventListener("click", () => modal.hidden = true);
modal.addEventListener("click", event => { if (event.target === modal) modal.hidden = true; });
document.addEventListener("keydown", event => { if (event.key === "Escape") modal.hidden = true; });
search.addEventListener("input", () => {
  const q = search.value.trim().toLowerCase();
  render(records.filter(item => !q || [pad(item.edition), item.edition, item.source_master, item.eyes, item.expression].join(" ").toLowerCase().includes(q)));
});

fetch(`${ROOT}/manifest.json`).then(response => response.json()).then(manifest => { records = manifest.records; render(records); }).catch(() => { count.textContent = "COLLECTION DATA COULD NOT LOAD — REFRESH TO RETRY"; });
