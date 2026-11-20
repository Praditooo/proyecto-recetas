// Recetas: generar, ver historial, calificar y eliminar.
const DIFFICULTY_CLASS = { "Fácil": "d-facil", "Media": "d-media", "Difícil": "d-dificil" };

function formatMinutes(total) {
  if (total < 60) return `${total} min`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

function chip(iconName, text, extraClass = "") {
  return el("span", { className: `chip ${extraClass}`.trim() }, icon(iconName), el("span", { textContent: text }));
}

function renderStars(recipe) {
  const current = recipe.rating || 0;
  return el("div", { className: "stars", role: "group", ariaLabel: current ? `Calificada con ${current} de 5` : "Sin calificar" },
    [1, 2, 3, 4, 5].map((n) => {
      const label = `Calificar con ${n} ${n === 1 ? "estrella" : "estrellas"}`;
      return el("button", {
        className: `icon-button star${n <= current ? " on" : ""}`,
        type: "button", title: label, ariaLabel: label, ariaPressed: String(n === current),
        onclick: () => rateRecipe(recipe.id, n),
      }, icon("star"));
    }),
  );
}

function renderRecipe(recipe) {
  const deleteLabel = `Eliminar ${recipe.name}`;
  return el("article", { className: "panel recipe" },
    el("header", { className: "recipe-head" },
      el("h3", { textContent: recipe.name }),
      el("div", { className: "chips" },
        chip("clock", formatMinutes(recipe.estimated_minutes)),
        chip("gauge", recipe.difficulty, DIFFICULTY_CLASS[recipe.difficulty] || ""),
      ),
    ),
    el("div", { className: "recipe-body" },
      el("section", {},
        el("h4", { textContent: "Ingredientes" }),
        el("ul", { className: "recipe-ingredients" }, recipe.ingredients.map((i) =>
          el("li", {},
            el("span", { textContent: i.name }),
            el("span", { textContent: `${formatQuantity(i.quantity)} ${i.unit}` }),
          ))),
      ),
      el("section", {},
        el("h4", { textContent: "Preparación" }),
        el("ol", { className: "recipe-steps" }, recipe.steps.map((step) => el("li", { textContent: step }))),
      ),
    ),
    el("footer", { className: "recipe-foot" },
      el("div", { className: "rating-box" },
        renderStars(recipe),
        recipe.rating
          ? [el("button", { className: "button ghost", type: "button", textContent: "Quitar", title: "Quitar estrellas", onclick: () => removeRating(recipe.id) })]
          : [],
      ),
      el("button", {
        className: "icon-button danger", type: "button", title: deleteLabel, ariaLabel: deleteLabel,
        onclick: () => deleteRecipe(recipe),
      }, icon("trash")),
    ),
  );
}

function loadingCard() {
  return el("article", { className: "panel recipe loading", ariaLive: "polite" },
    el("p", { className: "loading-title" }, el("span", { className: "spinner" }), el("span", { textContent: "Preparando tu receta…" })),
    el("div", { className: "skeleton w-70" }),
    el("div", { className: "skeleton w-50" }),
    el("div", { className: "skeleton w-85" }),
    el("div", { className: "skeleton w-70" }),
  );
}

function emptyHistory(filtered) {
  return filtered
    ? el("div", { className: "empty" },
        icon("search"),
        el("strong", { textContent: "Ninguna receta coincide con los filtros." }),
        el("span", { textContent: "Prueba con otra búsqueda o quita algún filtro." }))
    : el("div", { className: "empty" },
        icon("book"),
        el("strong", { textContent: "Aún no tienes recetas." }),
        el("span", { textContent: "Genera la primera con tu inventario." }));
}

// Historial: se piden PAGE_SIZE recetas por página según los filtros del formulario.
const PAGE_SIZE = 12;
const historyState = { shown: 0, total: 0 };

function historyQuery(offset, limit) {
  const params = new URLSearchParams();
  const data = new FormData(document.getElementById("history-filters"));
  for (const [key, value] of data) {
    const text = String(value).trim();
    if (text) params.set(key, text);
  }
  params.set("limit", limit);
  params.set("offset", offset);
  return params;
}

function hasActiveFilters() {
  const params = historyQuery(0, PAGE_SIZE);
  return ["q", "difficulty", "min_rating"].some((key) => params.has(key));
}

function updateHistoryFooter() {
  const count = document.getElementById("recipes-count");
  const { shown, total } = historyState;
  const noun = total === 1 ? "receta" : "recetas";
  count.textContent = !total ? "" : shown >= total ? `${total} ${noun}` : `Mostrando ${shown} de ${total} recetas`;
  document.getElementById("recipes-more").hidden = historyState.shown >= historyState.total;
}

// keep=true recarga la misma cantidad de recetas que ya se veían (tras calificar o eliminar).
async function loadRecipes({ keep = false } = {}) {
  const box = document.getElementById("recipes");
  const limit = keep ? Math.min(100, Math.max(PAGE_SIZE, historyState.shown)) : PAGE_SIZE;
  try {
    const { items, total } = await apiWithTotal(`/recipes?${historyQuery(0, limit)}`);
    historyState.shown = items.length;
    historyState.total = total;
    if (!items.length) {
      box.replaceChildren(emptyHistory(hasActiveFilters()));
    } else {
      box.replaceChildren(...items.map(renderRecipe));
    }
    updateHistoryFooter();
    loadStats();
  } catch (err) {
    showMsg(err.message);
  }
}

// Muestra el promedio de estrellas y cuantas recetas estan calificadas.
async function loadStats() {
  let box = document.getElementById("recipes-stats");
  if (!box) {
    box = el("p", { id: "recipes-stats", className: "history-stats" });
    document.getElementById("history-filters").after(box);
  }
  try {
    const stats = await api("/recipes/stats");
    box.textContent = stats.average_stars === null
      ? ""
      : `Promedio ${stats.average_stars.toFixed(1)} de 5 estrellas (${stats.rated} de ${stats.total} recetas calificadas)`;
    box.hidden = !box.textContent;
  } catch (err) {
    box.hidden = true;
  }
}

async function loadMoreRecipes() {
  try {
    const { items, total } = await apiWithTotal(`/recipes?${historyQuery(historyState.shown, PAGE_SIZE)}`);
    document.getElementById("recipes").append(...items.map(renderRecipe));
    historyState.shown += items.length;
    historyState.total = total;
    updateHistoryFooter();
  } catch (err) {
    showMsg(err.message);
  }
}

function initHistoryFilters() {
  const form = document.getElementById("history-filters");
  let timer;
  form.addEventListener("submit", (event) => event.preventDefault());
  form.addEventListener("change", () => loadRecipes());
  form.elements.q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => loadRecipes(), 300);
  });
  document.getElementById("recipes-more").addEventListener("click", loadMoreRecipes);
}

async function rateRecipe(id, stars) {
  try {
    await api(`/recipes/${id}/rating`, { method: "POST", json: { stars } });
    loadRecipes({ keep: true });
  } catch (err) {
    showMsg(err.message);
  }
}

async function removeRating(id) {
  try {
    await api(`/recipes/${id}/rating`, { method: "DELETE" });
    loadRecipes({ keep: true });
  } catch (err) {
    showMsg(err.message);
  }
}

async function deleteRecipe(recipe) {
  if (!confirm(`¿Eliminar "${recipe.name}" de tu historial?`)) return;
  try {
    await api(`/recipes/${recipe.id}`, { method: "DELETE" });
    showMsg("Receta eliminada.", true);
    loadRecipes({ keep: true });
  } catch (err) {
    showMsg(err.message);
  }
}

// Lee las preferencias del formulario; los campos vacíos no se envían.
function readGenerateOptions(form) {
  const data = new FormData(form);
  const options = {};
  if (data.get("diet")) options.diet = data.get("diet");
  if (data.get("max_minutes")) options.max_minutes = Number(data.get("max_minutes"));
  if (data.get("servings")) options.servings = Number(data.get("servings"));
  return options;
}

function initRecipes() {
  const form = document.getElementById("generate-form");
  const button = document.getElementById("generate");
  const label = button.querySelector(".label");
  const buttonIcon = button.querySelector(".icon");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const box = document.getElementById("recipes");
    const placeholder = loadingCard();
    const spinner = el("span", { className: "spinner" });
    button.disabled = true;
    buttonIcon.replaceWith(spinner);
    label.textContent = "Generando…";
    showMsg("");
    if (box.querySelector(".empty")) box.replaceChildren();
    box.prepend(placeholder);
    placeholder.scrollIntoView({ behavior: "smooth", block: "nearest" });
    try {
      await api("/recipes/generate", { method: "POST", json: readGenerateOptions(form) });
      await loadRecipes();
      const first = box.querySelector(".recipe");
      if (first) first.classList.add("fresh");
    } catch (err) {
      placeholder.remove();
      if (!box.children.length) box.replaceChildren(emptyHistory(hasActiveFilters()));
      showMsg(err.message);
    } finally {
      button.disabled = false;
      spinner.replaceWith(buttonIcon);
      label.textContent = "Generar receta";
    }
  });
  initHistoryFilters();
  loadRecipes();
}
