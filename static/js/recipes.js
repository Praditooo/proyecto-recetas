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

async function loadRecipes() {
  const box = document.getElementById("recipes");
  try {
    const recipes = await api("/recipes");
    if (!recipes.length) {
      box.replaceChildren(el("p", { textContent: "Aún no tienes recetas. Genera la primera con tu inventario." }));
      return;
    }
    box.replaceChildren(...recipes.map(renderRecipe));
  } catch (err) {
    showMsg(err.message);
  }
}

async function rateRecipe(id, stars) {
  try {
    await api(`/recipes/${id}/rating`, { method: "POST", json: { stars } });
    loadRecipes();
  } catch (err) {
    showMsg(err.message);
  }
}

async function deleteRecipe(id) {
  try {
    await api(`/recipes/${id}`, { method: "DELETE" });
    loadRecipes();
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
  loadRecipes();
}
