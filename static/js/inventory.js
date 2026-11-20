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
    if (counter) counter.textContent = items.length ? `${items.length} ingrediente(s)` : "";
    if (!items.length) {
      const msg = query
        ? `No se encontraron ingredientes que coincidan con "${query}".`
        : "Tu inventario está vacío. Agrega tu primer ingrediente.";
      list.replaceChildren(el("li", { textContent: msg }));
      return;
    }
    list.replaceChildren(...items.map((item) =>
      el("li", {},
        el("span", { textContent: `${item.name}: ${item.quantity} ${item.unit}` }),
        el("span", { className: "actions" },
          el("button", { className: "secondary", type: "button", textContent: "Editar", onclick: () => editIngredientInline(item) }),
          el("button", { className: "danger", type: "button", textContent: "Eliminar", onclick: () => deleteIngredient(item) }),
        ),
      ),
    ));
  } catch (err) {
    showMsg(err.message);
  }
}

function editIngredientInline(item) {
  const list = document.getElementById("ingredients");
  const items = Array.from(list.children);
  const li = items.find((node) => {
    const span = node.querySelector("span");
    return span && span.textContent.startsWith(item.name + ":");
  });
  if (!li) return;

  const nameInput = el("input", { type: "text", value: item.name, maxLength: 100, required: true });
  const qtyInput = el("input", { type: "number", value: item.quantity, min: "0.01", step: "any", required: true });
  const unitSelect = document.createElement("select");
  UNITS.forEach((u) => {
    const opt = document.createElement("option");
    opt.value = u;
    opt.textContent = u;
    if (u === item.unit) opt.selected = true;
    unitSelect.appendChild(opt);
  });

  const saveBtn = el("button", {
    type: "button", textContent: "Guardar",
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
    className: "secondary", type: "button", textContent: "Cancelar",
    onclick: () => loadIngredients(),
  });

  li.replaceChildren(
    el("span", { className: "inline-edit" },
      nameInput, qtyInput, unitSelect,
    ),
    el("span", { className: "actions" }, saveBtn, cancelBtn),
  );
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
