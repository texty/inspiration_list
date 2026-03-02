// Palette — one colour per category, assigned in sorted order
const PALETTE = [
  "#e54b4b", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
  "#14b8a6", "#a855f7", "#0ea5e9", "#22c55e", "#d97706",
  "#7c3aed", "#ef4444",
];

let allLinks = [];
let categoryColor = {};   // category → hex
let activeCategory = "all";
let searchQuery = "";

async function init() {
  try {
    const res = await fetch("links.json");
    allLinks = await res.json();
  } catch {
    document.getElementById("gallery").innerHTML =
      '<p class="empty">Could not load links.json — run the server with:<br><code>python3 -m http.server 8000</code></p>';
    return;
  }

  // Assign colours to categories
  const categories = [...new Set(allLinks.map(l => l.category))].sort();
  categories.forEach((cat, i) => {
    categoryColor[cat] = PALETTE[i % PALETTE.length];
  });

  renderFilters(categories);
  renderGallery();

  document.getElementById("search").addEventListener("input", e => {
    searchQuery = e.target.value.toLowerCase();
    renderGallery();
  });
}

// ── Filters ──────────────────────────────────────────────

function renderFilters(categories) {
  const nav = document.getElementById("filters");
  nav.innerHTML = "";

  const allPill = makePill("All", "all", "#52525b");
  setActive(allPill, "#52525b");
  nav.appendChild(allPill);

  categories.forEach(cat => {
    nav.appendChild(makePill(cat, cat, categoryColor[cat]));
  });
}

function makePill(label, value, color) {
  const btn = document.createElement("button");
  btn.className = "pill";
  btn.textContent = label;

  btn.addEventListener("click", () => {
    activeCategory = value;
    document.querySelectorAll(".pill").forEach(p => clearActive(p));
    setActive(btn, color);
    renderGallery();
  });

  return btn;
}

function setActive(btn, color) {
  btn.classList.add("active");
  btn.style.background = color;
}
function clearActive(btn) {
  btn.classList.remove("active");
  btn.style.background = "";
}

// ── Gallery ───────────────────────────────────────────────

function renderGallery() {
  const gallery = document.getElementById("gallery");

  let links = allLinks;

  if (activeCategory !== "all") {
    links = links.filter(l => l.category === activeCategory);
  }

  if (searchQuery) {
    links = links.filter(l =>
      l.title.toLowerCase().includes(searchQuery) ||
      l.excerpt.toLowerCase().includes(searchQuery) ||
      (l.note && l.note.toLowerCase().includes(searchQuery)) ||
      l.category.toLowerCase().includes(searchQuery)
    );
  }

  document.getElementById("count").textContent =
    links.length === allLinks.length
      ? `${allLinks.length} links`
      : `${links.length} of ${allLinks.length}`;

  if (links.length === 0) {
    gallery.innerHTML = '<p class="empty">No links found.</p>';
    return;
  }

  gallery.innerHTML = links.map(cardHTML).join("");
}

// ── Card ──────────────────────────────────────────────────

function cardHTML(link) {
  const color = categoryColor[link.category] || "#52525b";

  const imageHTML = link.cover_image
    ? `<img class="card-image" src="${esc(link.cover_image)}" alt=""
         loading="lazy" onerror="this.replaceWith(placeholder('${esc(color)}'))">`
    : `<div class="card-placeholder" style="background:${color}18">🔗</div>`;

  const excerptHTML = link.excerpt
    ? `<p class="card-excerpt">${esc(link.excerpt)}</p>`
    : "";

  const noteHTML = link.note
    ? `<p class="card-note">${esc(link.note)}</p>`
    : "";

  return `
    <a class="card" href="${esc(link.url)}" target="_blank" rel="noopener noreferrer">
      ${imageHTML}
      <div class="card-body">
        <span class="card-tag" style="background:${color}">${esc(link.category)}</span>
        <p class="card-title">${esc(link.title)}</p>
        ${excerptHTML}
        ${noteHTML}
      </div>
    </a>`;
}

// Called inline by onerror on broken images
function placeholder(color) {
  const div = document.createElement("div");
  div.className = "card-placeholder";
  div.style.background = color + "18";
  div.textContent = "🔗";
  return div;
}

function esc(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

init();
