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

function initRecipes() {
  const button = document.getElementById("generate");
  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Generando receta...";
    try {
      await api("/recipes/generate", { method: "POST" });
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
