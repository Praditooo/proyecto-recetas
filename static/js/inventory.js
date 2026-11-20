// Inventario personal: listar, agregar, editar cantidad y eliminar ingredientes.
async function loadIngredients() {
  const list = document.getElementById("ingredients");
  try {
    const items = await api("/ingredients");
    if (!items.length) {
      list.replaceChildren(el("li", { textContent: "Tu inventario está vacío. Agrega tu primer ingrediente." }));
      return;
    }
    list.replaceChildren(...items.map((item) =>
      el("li", {},
        el("span", { textContent: `${item.name}: ${item.quantity} ${item.unit}` }),
        el("span", { className: "actions" },
          el("button", { className: "secondary", type: "button", textContent: "Editar cantidad", onclick: () => editIngredient(item) }),
          el("button", { className: "danger", type: "button", textContent: "Eliminar", onclick: () => deleteIngredient(item) }),
        ),
      ),
    ));
  } catch (err) {
    showMsg(err.message);
  }
}

async function editIngredient(item) {
  const value = prompt(`Nueva cantidad de ${item.name} (${item.unit})`, item.quantity);
  if (value === null) return;
  try {
    await api(`/ingredients/${item.id}`, {
      method: "PUT",
      json: { name: item.name, quantity: Number(value), unit: item.unit },
    });
    showMsg("");
    loadIngredients();
  } catch (err) {
    showMsg(err.message);
  }
}

async function deleteIngredient(item) {
  try {
    await api(`/ingredients/${item.id}`, { method: "DELETE" });
    loadIngredients();
  } catch (err) {
    showMsg(err.message);
  }
}

function initInventory() {
  document.getElementById("ingredient-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/ingredients", {
        method: "POST",
        json: { name: form.get("name"), quantity: Number(form.get("quantity")), unit: form.get("unit") },
      });
      event.target.reset();
      event.target.elements.unit.value = "unidad";
      showMsg("");
      loadIngredients();
    } catch (err) {
      showMsg(err.message);
    }
  });
  loadIngredients();
}
