// Utilidades compartidas: cliente de la API, helpers de DOM y pantalla de acceso.
const API = "/api";

const token = () => localStorage.getItem("token");

// Aviso flotante. Los de éxito se ocultan solos; los errores quedan hasta cerrarlos o hasta el siguiente aviso.
let msgTimer;
function showMsg(text, ok = false) {
  const msg = document.getElementById("msg");
  clearTimeout(msgTimer);
  if (!text) { msg.hidden = true; return; }
  msg.querySelector(".msg-text").textContent = text;
  msg.querySelector("use").setAttribute("href", ok ? "#i-check" : "#i-alert");
  msg.className = ok ? "msg ok" : "msg";
  msg.setAttribute("role", ok ? "status" : "alert");
  msg.hidden = false;
  if (ok) msgTimer = setTimeout(() => { msg.hidden = true; }, 4000);
}

document.addEventListener("DOMContentLoaded", () => {
  const close = document.querySelector("#msg .msg-close");
  if (close) close.addEventListener("click", () => showMsg(""));
});

// Icono del sprite de base.html: icon("trash") -> <svg class="icon"><use href="#i-trash"></use></svg>
function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}

// Muestra el nombre del usuario en la barra superior.
async function loadUserName() {
  try {
    const me = await api("/auth/me");
    document.getElementById("user-name").textContent = me.full_name;
  } catch (_) { /* si falla, api() ya maneja la sesión expirada */ }
}

function logout() {
  localStorage.removeItem("token");
  location.href = "/";
}

// Crea un elemento sin usar innerHTML (el contenido del LLM nunca se interpreta como HTML).
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  children.flat().forEach((child) => node.append(child));
  return node;
}

const FIELD_LABELS = {
  email: "El correo",
  password: "La contraseña",
  full_name: "El nombre",
  name: "El nombre",
  quantity: "La cantidad",
  unit: "La unidad",
  max_minutes: "El tiempo máximo",
  servings: "Las porciones",
};

// Convierte los errores 422 de FastAPI en frases legibles en español.
function formatValidationError(errors) {
  return errors
    .map((e) => {
      const field = FIELD_LABELS[e.loc[e.loc.length - 1]] || "Un campo";
      switch (e.type) {
        case "string_too_short":
          return `${field} debe tener al menos ${e.ctx.min_length} caracteres`;
        case "string_too_long":
          return `${field} no puede superar ${e.ctx.max_length} caracteres`;
        case "missing":
          return `${field} es obligatorio`;
        case "greater_than":
          return `${field} debe ser mayor que ${e.ctx.gt}`;
        case "greater_than_equal":
          return `${field} debe ser al menos ${e.ctx.ge}`;
        case "less_than_equal":
          return `${field} no puede ser mayor que ${e.ctx.le}`;
        default:
          if (e.type === "value_error" && e.msg.startsWith("Value error, ")) {
            return e.msg.replace("Value error, ", "");
          }
          if (e.loc.includes("email")) return "El correo no es válido";
          return `${field} no es válido`;
      }
    })
    .join(". ");
}

// Hace la petición y lanza un Error con mensaje legible si falla; devuelve la Response.
async function apiRequest(path, options = {}) {
  const { json, ...rest } = options;
  const headers = { ...(rest.headers || {}) };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    rest.body = JSON.stringify(json);
  }
  const res = await fetch(API + path, { ...rest, headers });
  if (res.status === 401 && token()) {
    logout();
    throw new Error("Tu sesión expiró");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = formatValidationError(data.detail);
      else detail = "Revisa los datos ingresados";
    } catch (_) { /* respuesta sin JSON */ }
    throw new Error(detail);
  }
  return res;
}

async function api(path, options = {}) {
  const res = await apiRequest(path, options);
  return res.status === 204 ? null : res.json();
}

// Para listas paginadas: devuelve los elementos y el total de la cabecera X-Total-Count.
async function apiWithTotal(path, options = {}) {
  const res = await apiRequest(path, options);
  const items = await res.json();
  const header = res.headers.get("X-Total-Count");
  return { items, total: header === null ? items.length : Number(header) };
}

// Pestañas Iniciar sesión / Crear cuenta.
function selectAuthTab(name) {
  ["login", "register"].forEach((tab) => {
    const active = tab === name;
    document.getElementById(`tab-${tab}`).setAttribute("aria-selected", String(active));
    document.getElementById(`${tab}-form`).hidden = !active;
  });
}

function initAuthPage() {
  if (token()) { location.href = "/dashboard"; return; }

  document.getElementById("tab-login").addEventListener("click", () => selectAuthTab("login"));
  document.getElementById("tab-register").addEventListener("click", () => selectAuthTab("register"));

  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      const res = await fetch(API + "/auth/login", {
        method: "POST",
        body: new URLSearchParams({ username: form.get("email"), password: form.get("password") }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(res.status === 429 && data.detail ? data.detail : "Correo o contraseña incorrectos");
      }
      localStorage.setItem("token", (await res.json()).access_token);
      location.href = "/dashboard";
    } catch (err) {
      showMsg(err.message);
    }
  });

  document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/auth/register", {
        method: "POST",
        json: { email: form.get("email"), full_name: form.get("full_name"), password: form.get("password") },
      });
      event.target.reset();
      selectAuthTab("login");
      const login = document.getElementById("login-form");
      login.elements.email.value = form.get("email");
      login.elements.password.focus();
      showMsg("Cuenta creada. Ya puedes iniciar sesión.", true);
    } catch (err) {
      showMsg(err.message);
    }
  });
}