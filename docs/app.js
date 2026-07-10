const state = { manifest: null, house: "All Houses", query: "", selected: null, mode: "color" };

const modes = {
  color: { label: "8-BIT COLOR", alt: "8-bit color", folder: "characters" },
  "one-bit": { label: "1-BIT BLACK", alt: "one-bit black", folder: "one-bit" },
  block: { label: "1-BIT BLOCK", alt: "chunky one-bit black", folder: "block" },
};

const gallery = document.querySelector("#gallery");
const filters = document.querySelector("#filters");
const search = document.querySelector("#search");
const shownCount = document.querySelector("#shown-count");
const empty = document.querySelector("#empty");
const modal = document.querySelector("#modal");

function padded(id) { return String(id).padStart(3, "0"); }
function imageSource(id) { return `${modes[state.mode].folder}/${padded(id)}.png`; }

function matches(character) {
  if (state.house !== "All Houses" && character.house !== state.house) return false;
  const q = state.query.trim().toLowerCase();
  if (!q) return true;
  const text = [character.name, character.house, character.id, ...character.traits.flatMap(t => [t.name, t.code, t.category])].join(" ").toLowerCase();
  return text.includes(q);
}

function renderGallery() {
  const visible = state.manifest.characters.filter(matches);
  shownCount.textContent = `${String(visible.length).padStart(3, "0")} / ${state.manifest.count} SHOWN`;
  empty.hidden = visible.length !== 0;
  gallery.replaceChildren(...visible.map(character => {
    const card = document.createElement("button");
    card.className = "character-card";
    card.style.setProperty("--accent", character.accent);
    card.setAttribute("aria-label", `Inspect ${character.name}`);
    card.innerHTML = `<span class="image-well"><img src="${imageSource(character.id)}" alt="${character.name} — ${modes[state.mode].alt}" loading="lazy"></span><span class="card-meta"><span><b>#${padded(character.id)}</b><small>${character.house}</small></span><span class="inspect">↗</span></span>`;
    card.addEventListener("click", () => openCharacter(character));
    return card;
  }));
}

function renderFilters() {
  const names = ["All Houses", ...state.manifest.houses.map(house => house.name)];
  filters.replaceChildren(...names.map(name => {
    const button = document.createElement("button");
    button.textContent = name;
    button.className = name === state.house ? "active" : "";
    button.addEventListener("click", () => { state.house = name; renderFilters(); renderGallery(); });
    return button;
  }));
}

function renderHero() {
  const stack = document.querySelector("#hero-stack");
  stack.replaceChildren();
  [7, 18, 1].forEach((id, index) => {
    const character = state.manifest.characters[id - 1];
    const card = document.createElement("div");
    card.className = `stack-card stack-${index + 1}`;
    card.style.setProperty("--accent", character.accent);
    card.innerHTML = `<img src="${imageSource(id)}" alt=""><span>#${padded(id)}</span>`;
    stack.append(card);
  });
}

function renderStyleSwitch() {
  const switcher = document.querySelector("#style-switch");
  const options = Object.entries(modes).map(([id, mode]) => ({ id, label: mode.label }));
  switcher.replaceChildren(...options.map(option => {
    const button = document.createElement("button");
    button.textContent = option.label;
    button.className = state.mode === option.id ? "active" : "";
    button.setAttribute("aria-pressed", state.mode === option.id ? "true" : "false");
    button.addEventListener("click", () => setMode(option.id));
    return button;
  }));
}

function setMode(mode) {
  state.mode = mode;
  document.body.dataset.mode = mode;
  document.querySelector("#mode-label").textContent = modes[mode].label;
  renderStyleSwitch();
  renderHero();
  renderGallery();
  if (state.selected) {
    const art = document.querySelector("#detail-art");
    art.src = imageSource(state.selected.id);
    art.alt = `${state.selected.name} — ${modes[mode].alt}`;
  }
}

function openCharacter(character) {
  state.selected = character;
  document.querySelector("#detail-title").textContent = character.name;
  document.querySelector("#detail-motto").textContent = `“${character.motto}”`;
  document.querySelector("#detail-house").textContent = character.house;
  const image = document.querySelector("#detail-image");
  image.style.setProperty("--accent", character.accent);
  const art = document.querySelector("#detail-art");
  art.src = imageSource(character.id);
  art.alt = `${character.name} — ${modes[state.mode].alt}`;
  document.querySelector("#trait-list").innerHTML = character.traits.map(trait => `<div><span>${trait.category}</span><strong>${trait.name}</strong><code>${trait.code}</code></div>`).join("");
  modal.hidden = false;
  document.body.style.overflow = "hidden";
  document.querySelector("#close").focus();
}

function closeModal() {
  modal.hidden = true;
  document.body.style.overflow = "";
  state.selected = null;
}

document.querySelector("#close").addEventListener("click", closeModal);
modal.addEventListener("click", event => { if (event.target === modal) closeModal(); });
document.addEventListener("keydown", event => { if (event.key === "Escape" && !modal.hidden) closeModal(); });
search.addEventListener("input", event => { state.query = event.target.value; renderGallery(); });
document.querySelector("#copy").addEventListener("click", async event => {
  const character = state.selected;
  const traits = character.traits.map(trait => `${trait.category}: ${trait.name}`).join("; ");
  await navigator.clipboard.writeText(`${character.name} — ${character.house}\n${traits}\nReview: `);
  event.currentTarget.textContent = "COPIED";
  setTimeout(() => { event.currentTarget.textContent = "COPY REVIEW NOTE"; }, 1500);
});

fetch("characters/manifest.json")
  .then(response => { if (!response.ok) throw new Error("Manifest unavailable"); return response.json(); })
  .then(manifest => { state.manifest = manifest; document.body.dataset.mode = state.mode; renderStyleSwitch(); renderHero(); renderFilters(); renderGallery(); })
  .catch(() => {
    gallery.innerHTML = '<div class="empty-state">The gallery could not load. Please refresh the page.</div>';
  });
