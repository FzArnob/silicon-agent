const { contextBridge } = require("electron");

const BASE_URL = "http://127.0.0.1:8000";

async function request(path, method = "GET", body) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

const month = (value) => encodeURIComponent(value);

contextBridge.exposeInMainWorld("desktopApi", {
  health: () => request("/api/health"),
  getMeta: () => request("/api/meta"),

  listInputSets: () => request("/api/input-sets"),
  createInputSet: (values) => request("/api/input-sets", "POST", values),
  updateInputSet: (id, values) => request(`/api/input-sets/${id}`, "PUT", values),
  deleteInputSet: (id) => request(`/api/input-sets/${id}`, "DELETE"),

  getPlansheet: (value) => request(`/api/plansheets/${month(value)}`),
  savePlansheet: (value, body) => request(`/api/plansheets/${month(value)}`, "PUT", body),
  selectInputSet: (value, inputSetId) =>
    request(`/api/plansheets/${month(value)}/input-set`, "PUT", { input_set_id: inputSetId }),
  generatePlansheet: (value, inputSetId) =>
    request(`/api/plansheets/${month(value)}/generate`, "POST", { input_set_id: inputSetId }),
  deletePlansheet: (value) => request(`/api/plansheets/${month(value)}`, "DELETE"),
});
