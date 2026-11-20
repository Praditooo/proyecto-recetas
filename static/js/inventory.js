// Inventario personal: listar, agregar, buscar, editar en línea y eliminar ingredientes.
const UNITS = [
  "unidad", "g", "kg", "mg", "oz", "lb",
  "ml", "l", "taza", "cucharada", "cucharadita",
  "litro", "pieza", "rebanada", "diente", "manojo",
  "pizca", "lata", "paquete", "sobre",
];

async function loadIngredients(query) {
  const list = document.getElementById("ingredients");
  const counter = document.getElementById("ingredients-count");
  try {
    const path = query ? `/ingredients?q=${encodeURIComponent(query)}` : "/ingredients";
    const items = await api(path);
    if (counter) {
      const noun = items.length === 1 ? "ingrediente" : "ingredientes";
      counter.textContent = items.length ? `${items.length} ${noun}` : "";
    }
    if (!items.length) {
      const empty = query
        ? el("li", { className: "empty" }, el("span", { textContent: `Nada coincide con "${query}".` }))
        : el("li", { className: "empty" },
            icon("basket"),
            el("strong", { textContent: "Tu inventario está vacío" }),
            el("span", { textContent: "Agrega lo que tienes en casa para generar recetas." }),
          );
      list.replaceChildren(empty);
      return;
    }
    list.replaceChildren(...items.map((item) => {
      const li = el("li", {},
        el("span", { className: "ingredient-name", textContent: item.name }),
        el("span", { className: "ingredient-qty", textContent: `${formatQuantity(item.quantity)} ${item.unit}` }),
        el("span", { className: "actions" },
          iconButton("edit", `Editar ${item.name}`, () => editIngredientInline(item)),
          iconButton("trash", `Eliminar ${item.name}`, () => deleteIngredient(item), "danger"),
        ),
      );
      li.dataset.id = item.id;
      return li;
    }));
  } catch (err) {
    showMsg(err.message);
  }
}

// 500 -> "500", 0.25 -> "0.25", 1.3333333 -> "1.33"
function formatQuantity(value) {
  return String(Math.round(value * 100) / 100);
}

function iconButton(name, label, onclick, variant = "") {
  return el("button", {
    className: `icon-button ${variant}`.trim(), type: "button", title: label, ariaLabel: label, onclick,
  }, icon(name));
}

function editIngredientInline(item) {
  const li = document.querySelector(`#ingredients li[data-id="${item.id}"]`);
  if (!li) return;
  li.classList.add("editing");

  const nameInput = el("input", { type: "text", value: item.name, maxLength: 100, required: true, ariaLabel: "Nombre" });
  const qtyInput = el("input", { type: "number", value: item.quantity, min: "0.01", step: "any", required: true, ariaLabel: "Cantidad" });
  const unitSelect = document.createElement("select");
  unitSelect.setAttribute("aria-label", "Unidad");
  UNITS.forEach((u) => {
    const opt = document.createElement("option");
    opt.value = u;
    opt.textContent = u;
    if (u === item.unit) opt.selected = true;
    unitSelect.appendChild(opt);
  });

  const saveBtn = el("button", {
    className: "button primary", type: "button", textContent: "Guardar",
    onclick: async () => {
      try {
        await api(`/ingredients/${item.id}`, {
          method: "PUT",
          json: { name: nameInput.value, quantity: Number(qtyInput.value), unit: unitSelect.value },
        });
        showMsg("");
        loadIngredients();
      } catch (err) {
        showMsg(err.message);
      }
    },
  });
  const cancelBtn = el("button", {
    className: "button ghost", type: "button", textContent: "Cancelar",
    onclick: () => loadIngredients(),
  });

  li.replaceChildren(
    el("span", { className: "inline-edit" },
      nameInput, qtyInput, unitSelect,
    ),
    el("span", { className: "actions" }, cancelBtn, saveBtn),
  );
  // Enter guarda y Escape cancela.
  li.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); saveBtn.click(); }
    if (event.key === "Escape") loadIngredients();
  });
  nameInput.focus();
}

async function deleteIngredient(item) {
  if (!confirm(`¿Eliminar "${item.name}" del inventario?`)) return;
  try {
    await api(`/ingredients/${item.id}`, { method: "DELETE" });
    loadIngredients();
  } catch (err) {
    showMsg(err.message);
  }
}

function initInventory() {
  // Reemplazar input de unidad por select con unidades predefinidas
  const unitInput = document.querySelector('#ingredient-form input[name="unit"]');
  if (unitInput) {
    const unitSelect = document.createElement("select");
    unitSelect.name = "unit";
    unitSelect.required = true;
    UNITS.forEach((u) => {
      const opt = document.createElement("option");
      opt.value = u;
      opt.textContent = u;
      if (u === "unidad") opt.selected = true;
      unitSelect.appendChild(opt);
    });
    unitInput.parentNode.replaceChild(unitSelect, unitInput);
  }

  document.getElementById("ingredient-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/ingredients", {
        method: "POST",
        json: { name: form.get("name"), quantity: Number(form.get("quantity")), unit: form.get("unit") },
      });
      event.target.reset();
      // Restaurar unidad por defecto en el select
      const sel = event.target.elements.unit;
      if (sel) sel.value = "unidad";
      showMsg("");
      event.target.elements.name.focus();
      loadIngredients();
    } catch (err) {
      showMsg(err.message);
    }
  });

  // Campo de búsqueda
  const searchInput = document.getElementById("ingredient-search");
  if (searchInput) {
    let debounce;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        const q = searchInput.value.trim();
        loadIngredients(q || undefined);
      }, 300);
    });
  }

  loadIngredients();
}
