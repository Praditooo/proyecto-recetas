// Recetas: generar, ver historial, calificar y eliminar.
function renderRecipe(recipe) {
  const stars = el("div", { className: "stars" },
    [1, 2, 3, 4, 5].map((n) =>
      el("button", {
        className: "star",
        type: "button",
        title: `${n} ${n === 1 ? "estrella" : "estrellas"}`,
        textContent: n <= (recipe.rating || 0) ? "★" : "☆",
        onclick: () => rateRecipe(recipe.id, n),
      }),
    ),
  );

  return el("article", { className: "panel" },
    el("h3", { textContent: recipe.name }),
    el("p", { className: "meta", textContent: `${recipe.estimated_minutes} min, dificultad ${recipe.difficulty.toLowerCase()}` }),
    el("h4", { textContent: "Ingredientes" }),
    el("ul", {}, recipe.ingredients.map((i) => el("li", { textContent: `${i.name}: ${i.quantity} ${i.unit}` }))),
    el("h4", { textContent: "Preparación" }),
    el("ol", {}, recipe.steps.map((step) => el("li", { textContent: step }))),
    stars,
    el("button", { className: "danger", type: "button", textContent: "Eliminar receta", onclick: () => deleteRecipe(recipe.id) }),
  );
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
  count.textContent = historyState.total ? `Mostrando ${historyState.shown} de ${historyState.total} recetas` : "";
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
      const text = hasActiveFilters()
        ? "Ninguna receta coincide con los filtros."
        : "Aún no tienes recetas. Genera la primera con tu inventario.";
      box.replaceChildren(el("p", { textContent: text }));
    } else {
      box.replaceChildren(...items.map(renderRecipe));
    }
    updateHistoryFooter();
  } catch (err) {
    showMsg(err.message);
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

async function deleteRecipe(id) {
  try {
    await api(`/recipes/${id}`, { method: "DELETE" });
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
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = "Generando receta...";
    try {
      await api("/recipes/generate", { method: "POST", json: readGenerateOptions(form) });
      showMsg("");
      await loadRecipes();
    } catch (err) {
      showMsg(err.message);
    } finally {
      button.disabled = false;
      button.textContent = "Generar receta";
    }
  });
  initHistoryFilters();
  loadRecipes();
}
