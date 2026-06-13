(() => {
  "use strict";

  const REQUIRED_COLUMNS = [
    "post_id", "upload_date", "upload_time",
    "title", "description", "hashtags", "keywords",
    "category", "sub_category_name", "series_name", "episode_number",
    "landscape_video_path", "landscape_thumbnail_path",
    "portrait_video_path", "portrait_thumbnail_path",
    "ai_flag", "kids_flag", "status"
  ];

  const state = {
    currentMonth: getCurrentMonth(),
    columns: [...REQUIRED_COLUMNS],
    rows: [],
    exists: false,
    dirty: false,
    dirtyRows: new Set(),
    undoStack: [],
    isLoading: false,
    generating: false,
  };

  const dom = {
    monthButton: document.getElementById("monthButton"),
    monthModal: document.getElementById("monthModal"),
    monthInput: document.getElementById("monthInput"),
    monthCancel: document.getElementById("monthCancel"),
    monthApply: document.getElementById("monthApply"),
    autoPilotToggle: document.getElementById("autoPilotToggle"),
    statusText: document.getElementById("statusText"),
    spinner: document.getElementById("spinner"),
    saveButton: document.getElementById("saveButton"),
    generateButton: document.getElementById("generateButton"),
    removeButton: document.getElementById("removeButton"),
    undoButton: document.getElementById("undoButton"),
    tableWrap: document.getElementById("tableWrap"),
    table: document.getElementById("plansheetTable"),
    thead: document.querySelector("#plansheetTable thead"),
    tbody: document.querySelector("#plansheetTable tbody"),
    emptyState: document.getElementById("emptyState"),
    skeleton: document.getElementById("skeleton"),
    toastHost: document.getElementById("toastHost"),
  };

  function init() {
    bindEvents();
    initAutoPilot();
    setMonth(state.currentMonth);
    void loadPlansheet();
  }

  function bindEvents() {
    dom.monthButton.addEventListener("click", openMonthModal);
    dom.monthCancel.addEventListener("click", closeMonthModal);
    dom.monthApply.addEventListener("click", applyMonthSelection);

    dom.generateButton.addEventListener("click", onGenerateClicked);
    dom.removeButton.addEventListener("click", onRemoveClicked);
    dom.saveButton.addEventListener("click", () => void savePlansheet());
    dom.undoButton.addEventListener("click", undoLastChange);

    window.addEventListener("keydown", onGlobalKeyDown);

    dom.autoPilotToggle.addEventListener("change", () => {
      localStorage.setItem("plansheet:auto_pilot", dom.autoPilotToggle.checked ? "1" : "0");
      showToast(dom.autoPilotToggle.checked ? "Auto Pilot enabled" : "Auto Pilot disabled", "ok");
    });

    dom.monthModal.addEventListener("click", (event) => {
      if (event.target === dom.monthModal) closeMonthModal();
    });
  }

  function initAutoPilot() {
    const persisted = localStorage.getItem("plansheet:auto_pilot");
    dom.autoPilotToggle.checked = persisted === "1";
  }

  function getCurrentMonth() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    return `${now.getFullYear()}-${month}`;
  }

  function setMonth(month) {
    state.currentMonth = month;
    dom.monthButton.textContent = month;
    dom.monthInput.value = month;
  }

  function openMonthModal() {
    dom.monthInput.value = state.currentMonth;
    dom.monthModal.classList.remove("hidden");
  }

  function closeMonthModal() {
    dom.monthModal.classList.add("hidden");
  }

  function applyMonthSelection() {
    const selected = dom.monthInput.value;
    if (!/^\d{4}-\d{2}$/.test(selected)) {
      showToast("Please pick a valid month.", "error");
      return;
    }
    if (state.dirty) {
      const ok = window.confirm("You have unsaved changes. Switch month and discard them?");
      if (!ok) return;
    }
    setMonth(selected);
    closeMonthModal();
    void loadPlansheet();
  }

  async function loadPlansheet() {
    setLoading(true);
    showSkeleton(true);
    hideTableAndEmpty();

    try {
      const data = await apiGet(`/api/plansheet?month=${encodeURIComponent(state.currentMonth)}`);
      state.exists = !!data.exists;
      state.columns = normalizeColumns(data.columns || REQUIRED_COLUMNS);
      state.rows = Array.isArray(data.rows) ? data.rows.map(cloneRow) : [];
      resetDirtyState();
      syncActionButtons();
      updateStatusText();

      if (!state.exists || state.rows.length === 0) {
        showEmptyState();
      } else {
        renderTable();
        showTable();
      }
    } catch (error) {
      showToast(`Failed to load plansheet: ${error.message}`, "error");
      state.exists = false;
      state.rows = [];
      syncActionButtons();
      showEmptyState();
    } finally {
      setLoading(false);
      showSkeleton(false);
    }
  }

  function normalizeColumns(sourceColumns) {
    const seen = new Set();
    const ordered = [];

    for (const col of sourceColumns) {
      if (typeof col === "string" && !seen.has(col)) {
        ordered.push(col);
        seen.add(col);
      }
    }

    for (const col of REQUIRED_COLUMNS) {
      if (!seen.has(col)) {
        ordered.push(col);
        seen.add(col);
      }
    }

    return ordered;
  }

  function cloneRow(row) {
    const out = {};
    for (const col of state.columns) {
      out[col] = String(row[col] ?? "");
    }
    return out;
  }

  function resetDirtyState() {
    state.dirty = false;
    state.dirtyRows.clear();
    state.undoStack = [];
    syncDirtyUi();
  }

  function syncActionButtons() {
    const hasFile = state.exists;
    dom.generateButton.classList.toggle("hidden", hasFile);
    dom.removeButton.classList.toggle("hidden", !hasFile);
  }

  function updateStatusText() {
    const monthText = `Selected month: ${state.currentMonth}`;
    const fileText = state.exists
      ? `Plansheet loaded (${state.rows.length} rows).`
      : "Plansheet not found. Generate to start.";
    dom.statusText.textContent = `${monthText} | ${fileText}`;
  }

  function renderTable() {
    renderHeader();
    renderBody();
  }

  function renderHeader() {
    dom.thead.innerHTML = "";
    const row = document.createElement("tr");
    for (const col of state.columns) {
      const th = document.createElement("th");
      th.textContent = col;
      th.dataset.column = col;
      row.appendChild(th);
    }
    dom.thead.appendChild(row);
  }

  function renderBody() {
    dom.tbody.innerHTML = "";
    const frag = document.createDocumentFragment();

    state.rows.forEach((rowData, rowIndex) => {
      const tr = document.createElement("tr");
      tr.dataset.row = String(rowIndex);

      state.columns.forEach((column, colIndex) => {
        const td = document.createElement("td");
        td.className = "cell";
        td.dataset.column = column;

        const wrap = document.createElement("div");
        wrap.className = "cell-wrap";

        const isLongText = true;
        const readOnly = column === "post_id";
        const value = rowData[column] ?? "";

        const control = document.createElement("textarea");
        control.className = "cell-control";
        control.value = value;
        control.dataset.row = String(rowIndex);
        control.dataset.col = column;
        control.dataset.colIndex = String(colIndex);
        control.dataset.rowIndex = String(rowIndex);

        control.title = value;
        if (readOnly) {
          control.readOnly = true;
          control.tabIndex = -1;
        }

        control.addEventListener("input", onCellInput);
        control.addEventListener("keydown", onCellKeyDown);

        const error = document.createElement("div");
        error.className = "cell-error";

        wrap.appendChild(control);
        wrap.appendChild(error);
        td.appendChild(wrap);
        tr.appendChild(td);
      });

      frag.appendChild(tr);
    });

    dom.tbody.appendChild(frag);

    for (const textarea of dom.tbody.querySelectorAll("textarea.cell-control")) {
      syncTextareaOverflow(textarea);
    }
  }

  function onCellInput(event) {
    const control = event.currentTarget;
    const rowIndex = Number(control.dataset.row);
    const column = control.dataset.col;

    const oldValue = state.rows[rowIndex][column] ?? "";
    const nextValue = control.value;
    if (oldValue === nextValue) return;

    state.undoStack.push({ rowIndex, column, oldValue, nextValue });
    if (state.undoStack.length > 300) state.undoStack.shift();

    state.rows[rowIndex][column] = nextValue;
    control.title = nextValue;
    state.dirty = true;
    state.dirtyRows.add(rowIndex);

    validateCell(control, column, nextValue);
    updateDirtyRowsUi();
    syncDirtyUi();

    if (control.tagName === "TEXTAREA") syncTextareaOverflow(control);
  }

  function onCellKeyDown(event) {
    const control = event.currentTarget;
    if (event.key === "Enter" && !event.shiftKey && control.tagName !== "TEXTAREA") {
      event.preventDefault();
      moveDown(control);
    }
  }

  function moveDown(control) {
    const row = Number(control.dataset.rowIndex);
    const col = Number(control.dataset.colIndex);
    const next = document.querySelector(`[data-row-index="${row + 1}"][data-col-index="${col}"]`);
    if (next && next instanceof HTMLElement && !next.readOnly) {
      next.focus();
      next.select?.();
    }
  }

  function validateCell(control, column, value) {
    const cell = control.closest("td");
    if (!cell) return;
    const errorEl = cell.querySelector(".cell-error");
    if (!errorEl) return;

    let message = "";
    if (column === "upload_date" && value && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      message = "Expected YYYY-MM-DD";
    }
    if (column === "upload_time" && value && !/^([01]\d|2[0-3]):[0-5]\d$/.test(value)) {
      message = "Expected HH:mm (24-hour)";
    }

    if (message) {
      cell.classList.add("invalid");
      errorEl.textContent = message;
    } else {
      cell.classList.remove("invalid");
      errorEl.textContent = "";
    }
  }

  function updateDirtyRowsUi() {
    for (const tr of dom.tbody.querySelectorAll("tr")) {
      const rowIndex = Number(tr.dataset.row);
      tr.classList.toggle("dirty-row", state.dirtyRows.has(rowIndex));
    }
  }

  function syncDirtyUi() {
    dom.saveButton.classList.toggle("hidden", !state.dirty);
    dom.undoButton.classList.toggle("hidden", state.undoStack.length === 0);
  }

  function undoLastChange() {
    const last = state.undoStack.pop();
    if (!last) return;

    state.rows[last.rowIndex][last.column] = last.oldValue;

    const selector = `[data-row="${last.rowIndex}"][data-col="${last.column}"]`;
    const control = dom.tbody.querySelector(selector);
    if (control) {
      control.value = last.oldValue;
      validateCell(control, last.column, last.oldValue);
      if (control.tagName === "TEXTAREA") syncTextareaOverflow(control);
    }

    recomputeDirtyState();
    updateDirtyRowsUi();
    syncDirtyUi();
  }

  function recomputeDirtyState() {
    // If at least one undo entry remains, there are unsaved changes.
    // This keeps behavior predictable in-session without expensive deep comparisons.
    state.dirty = state.undoStack.length > 0;
    if (!state.dirty) {
      state.dirtyRows.clear();
    }
  }

  function collectValidationErrors() {
    const invalidCells = dom.tbody.querySelectorAll("td.invalid");
    return invalidCells.length;
  }

  async function savePlansheet() {
    if (!state.exists) {
      showToast("No plansheet file to save.", "error");
      return;
    }

    const invalidCount = collectValidationErrors();
    if (invalidCount > 0) {
      showToast(`Please fix ${invalidCount} invalid field(s) before saving.`, "error");
      return;
    }

    try {
      setLoading(true);
      await apiPost("/api/plansheet/save", {
        month: state.currentMonth,
        columns: state.columns,
        rows: state.rows,
      });
      resetDirtyState();
      showToast("Plansheet saved successfully.", "ok");
      updateStatusText();
    } catch (error) {
      state.dirty = true;
      syncDirtyUi();
      showToast(`Save failed: ${error.message}`, "error");
    } finally {
      setLoading(false);
    }
  }

  async function onGenerateClicked() {
    if (state.generating) return;

    state.generating = true;
    dom.generateButton.disabled = true;
    dom.generateButton.textContent = "Generating...";
    setLoading(true);

    try {
      await apiPost("/api/plansheet/generate", { month: state.currentMonth });
      showToast("Plansheet generated.", "ok");
      await loadPlansheet();
    } catch (error) {
      showToast(`Generate failed: ${error.message}`, "error");
    } finally {
      state.generating = false;
      dom.generateButton.disabled = false;
      dom.generateButton.textContent = "Generate Plansheet";
      setLoading(false);
    }
  }

  async function onRemoveClicked() {
    const confirmed = window.confirm(`Remove plansheet for ${state.currentMonth}?`);
    if (!confirmed) return;

    try {
      setLoading(true);
      await apiDelete(`/api/plansheet?month=${encodeURIComponent(state.currentMonth)}`);
      state.exists = false;
      state.rows = [];
      resetDirtyState();
      syncActionButtons();
      updateStatusText();
      hideTableAndEmpty();
      showEmptyState();
      showToast("Plansheet removed.", "ok");
    } catch (error) {
      showToast(`Remove failed: ${error.message}`, "error");
    } finally {
      setLoading(false);
    }
  }

  function showTable() {
    dom.tableWrap.classList.remove("hidden");
    dom.emptyState.classList.add("hidden");
  }

  function showEmptyState() {
    dom.emptyState.classList.remove("hidden");
    dom.tableWrap.classList.add("hidden");
  }

  function hideTableAndEmpty() {
    dom.emptyState.classList.add("hidden");
    dom.tableWrap.classList.add("hidden");
  }

  function showSkeleton(show) {
    dom.skeleton.classList.toggle("hidden", !show);
  }

  function setLoading(loading) {
    state.isLoading = loading;
    dom.spinner.classList.toggle("hidden", !loading);
  }

  async function apiGet(url) {
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Request failed");
    }
    return payload;
  }

  async function apiPost(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Request failed");
    }
    return payload;
  }

  async function apiDelete(url) {
    const response = await fetch(url, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Request failed");
    }
    return payload;
  }

  function showToast(message, type = "ok") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    dom.toastHost.appendChild(toast);

    window.setTimeout(() => {
      toast.remove();
    }, 3200);
  }

  function onGlobalKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      void savePlansheet();
      return;
    }

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      undoLastChange();
    }
  }

  function syncTextareaOverflow(textarea) {
    const hasOverflow = textarea.scrollHeight > textarea.clientHeight + 1;
    textarea.classList.toggle("has-overflow", hasOverflow);
  }

  init();
})();
