const { contextBridge } = require("electron");

const BASE_URL = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || "Request failed");
  }
  return payload;
}

contextBridge.exposeInMainWorld("desktopApi", {
  health: () => request("/api/health"),
  getPlansheet: (month) => request(`/api/plansheets/${encodeURIComponent(month)}`),
  savePlansheet: (month, body) => request(`/api/plansheets/${encodeURIComponent(month)}`, {
    method: "PUT",
    body: JSON.stringify(body || {}),
  }),
  generatePlansheet: (month, body) => request(`/api/plansheets/${encodeURIComponent(month)}/generate`, {
    method: "POST",
    body: JSON.stringify(body || {}),
  }),
  deletePlansheet: (month) => request(`/api/plansheets/${encodeURIComponent(month)}`, {
    method: "DELETE",
  }),
});
