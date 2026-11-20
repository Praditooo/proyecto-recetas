// Utilidades compartidas: cliente de la API, helpers de DOM y pantalla de acceso.
const API = "/api";

const token = () => localStorage.getItem("token");

function showMsg(text, ok = false) {
  const msg = document.getElementById("msg");
  msg.textContent = text;
  msg.className = ok ? "msg ok" : "msg";
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

async function api(path, options = {}) {
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
  return res.status === 204 ? null : res.json();
}

function initAuthPage() {
  if (token()) { location.href = "/dashboard"; return; }

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
      showMsg("Cuenta creada. Ya puedes iniciar sesión.", true);
    } catch (err) {
      showMsg(err.message);
    }
  });
}