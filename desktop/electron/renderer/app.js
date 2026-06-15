(() => {
  const BOOLEAN_COLUMNS = new Set(["ai_flag", "kids_flag"]);
  const STATUS_VALUES = ["PLANNED", "FAILED", "COMPLETED", "PARTIALLY COMPLETED"];

  const REQUIRED_COLUMNS = [
    "post_id", "upload_date", "upload_time",
    "title", "description", "hashtags", "keywords",
    "category", "sub_category_name", "series_name", "episode_number",
    "landscape_video_path", "landscape_thumbnail_path",
    "portrait_video_path", "portrait_thumbnail_path",
    "ai_flag", "kids_flag", "status",
  ];

  const INPUT_FIELDS = [
    { key: "channel_name", label: "Channel Name" },
    { key: "category", label: "Category" },
    { key: "sub_category_name", label: "Sub Category" },
    { key: "series_name", label: "Series Name" },
    { key: "posts_per_week", label: "Posts Per Week", type: "number" },
    { key: "timezone", label: "Timezone" },
    { key: "storage_path", label: "Storage Path" },
    { key: "target_audience", label: "Target Audience (comma-separated)" },
    { key: "special_instructions", label: "Special Instructions", type: "textarea" },
  ];

  const state = {
    month: getCurrentMonth(),
    pickerYear: Number(getCurrentMonth().slice(0, 4)),
    input: {},
    rows: [],
    baselineRows: [],
    columns: [...REQUIRED_COLUMNS],
    exists: false,
    dirty: false,
    inputDirty: false,
    rowsDirty: false,
    baselineInput: {},
    baselineInputSig: "",
    baselineRowsSig: "",
    undoStack: [],
    busy: false,
  };

  const dom = {
    monthButton: document.getElementById("monthButton"),
    monthPicker: document.getElementById("monthPicker"),
    monthPickerYear: document.getElementById("monthPickerYear"),
    monthPrevYear: document.getElementById("monthPrevYear"),
    monthNextYear: document.getElementById("monthNextYear"),
    monthGrid: document.getElementById("monthGrid"),
    monthThis: document.getElementById("monthThis"),
    toggleInputButton: document.getElementById("toggleInputButton"),
    closeInputButton: document.getElementById("closeInputButton"),
    inputDrawer: document.getElementById("inputDrawer"),
    drawerOverlay: document.getElementById("drawerOverlay"),
    generateButton: document.getElementById("generateButton"),
    saveButton: document.getElementById("saveButton"),
    saveInputButton: document.getElementById("saveInputButton"),
    removeButton: document.getElementById("removeButton"),
    undoButton: document.getElementById("undoButton"),
    statusText: document.getElementById("statusText"),
    busyText: document.getElementById("busyText"),
    inputForm: document.getElementById("inputForm"),
    tableWrap: document.getElementById("tableWrap"),
    emptyState: document.getElementById("emptyState"),
    thead: document.querySelector("#plansheetTable thead"),
    tbody: document.querySelector("#plansheetTable tbody"),
    toastHost: document.getElementById("toastHost"),
  };

  function getCurrentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  }

  function init() {
    dom.monthButton.textContent = formatMonthLabel(state.month);
    bindEvents();
    void checkHealthAndLoad();
  }

  async function checkHealthAndLoad() {
    try {
      await window.desktopApi.health();
      setStatus("Backend ready");
      await loadMonth();
    } catch (error) {
      setStatus(`Backend unavailable: ${error.message}`);
      showToast(`Backend unavailable: ${error.message}`, "error");
    }
  }

  function bindEvents() {
    dom.monthButton.addEventListener("click", toggleMonthPicker);
    dom.monthPrevYear.addEventListener("click", () => {
      state.pickerYear -= 1;
      renderMonthPicker();
    });
    dom.monthNextYear.addEventListener("click", () => {
      state.pickerYear += 1;
      renderMonthPicker();
    });
    dom.monthThis.addEventListener("click", async () => {
      await selectMonth(getCurrentMonth());
      closeMonthPicker();
    });
    dom.monthGrid.addEventListener("click", async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const button = target.closest(".month-cell");
      if (!(button instanceof HTMLElement)) return;
      if (button.classList.contains("is-disabled")) return;
      const month = button.dataset.month;
      if (!month) return;
      await selectMonth(`${state.pickerYear}-${month}`);
      closeMonthPicker();
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!dom.monthPicker.contains(target) && !dom.monthButton.contains(target)) {
        closeMonthPicker();
      }

      if (!(target instanceof Element) || !target.closest(".cell-picker")) {
        closeAllCellPickers();
      }
    });

    dom.generateButton.addEventListener("click", () => void generateMonth());
    dom.saveButton.addEventListener("click", () => void saveMonth());
    dom.removeButton.addEventListener("click", () => void removeMonth());
    dom.undoButton.addEventListener("click", undoLastChange);
    dom.toggleInputButton.addEventListener("click", toggleInputDrawer);
    dom.closeInputButton.addEventListener("click", closeInputDrawer);
    dom.drawerOverlay.addEventListener("click", closeInputDrawer);
    dom.saveInputButton.addEventListener("click", () => void saveMonth());

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeInputDrawer();
        closeMonthPicker();
        closeAllCellPickers();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void saveMonth();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        undoLastChange();
      }
    });
  }

  async function loadMonth() {
    setBusy(true, "Loading month...");
    try {
      const payload = await window.desktopApi.getPlansheet(state.month);
      state.exists = !!payload.exists;
      state.columns = Array.isArray(payload.columns) ? payload.columns : [...REQUIRED_COLUMNS];
      state.rows = Array.isArray(payload.rows) ? payload.rows.map((row) => ({ ...row })) : [];
      state.input = payload.input || {};
      state.undoStack = [];
      updateBaselines();
      recomputeDirtyState();
      syncGenerateButtonLabel();
      renderInputForm();
      renderTable();
      syncButtons();
      syncInputDirtyUi();
      updateStatus();
      dom.monthButton.textContent = formatMonthLabel(state.month);
    } catch (error) {
      showToast(`Load failed: ${error.message}`, "error");
    } finally {
      setBusy(false, "");
    }
  }

  function renderInputForm() {
    dom.inputForm.innerHTML = "";
    const fragment = document.createDocumentFragment();

    for (const field of INPUT_FIELDS) {
      const row = document.createElement("div");
      row.className = "input-row";

      const label = document.createElement("label");
      label.textContent = field.label;

      const control = field.type === "textarea"
        ? document.createElement("textarea")
        : document.createElement("input");

      if (field.type === "number") {
        control.type = "number";
        control.min = "1";
      } else if (field.type !== "textarea") {
        control.type = "text";
      }

      const rawValue = state.input[field.key];
      if (field.key === "target_audience") {
        control.value = Array.isArray(rawValue) ? rawValue.join(", ") : String(rawValue || "");
      } else {
        control.value = rawValue == null ? "" : String(rawValue);
      }

      control.dataset.key = field.key;
      control.addEventListener("input", onInputConfigChanged);
      control.classList.toggle("modified-field", isInputFieldModified(field.key));
      if (field.type === "textarea") {
        control.addEventListener("input", () => autoGrowTextarea(control));
      }

      row.appendChild(label);
      row.appendChild(control);
      fragment.appendChild(row);

      if (field.type === "textarea") {
        window.requestAnimationFrame(() => autoGrowTextarea(control));
      }
    }

    dom.inputForm.appendChild(fragment);
  }

  function onInputConfigChanged(event) {
    const control = event.currentTarget;
    const key = control.dataset.key;
    if (!key) return;

    let value = control.value;
    if (key === "posts_per_week") {
      value = Number(value || 0);
    }
    if (key === "target_audience") {
      value = String(value)
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }

    state.input[key] = value;
    control.classList.toggle("modified-field", isInputFieldModified(key));
    recomputeDirtyState();
    syncInputDirtyUi();
    syncButtons();
    updateStatus();
  }

  function renderTable() {
    dom.thead.innerHTML = "";
    dom.tbody.innerHTML = "";

    if (!state.exists || state.rows.length === 0) {
      dom.tableWrap.classList.add("hidden");
      dom.emptyState.classList.remove("hidden");
      return;
    }

    dom.emptyState.classList.add("hidden");
    dom.tableWrap.classList.remove("hidden");

    const headerRow = document.createElement("tr");
    for (const column of state.columns) {
      const th = document.createElement("th");
      th.textContent = column;
      th.dataset.column = column;
      headerRow.appendChild(th);
    }
    dom.thead.appendChild(headerRow);

    const fragment = document.createDocumentFragment();
    state.rows.forEach((row, rowIndex) => {
      const tr = document.createElement("tr");
      state.columns.forEach((column) => {
        const td = document.createElement("td");
        td.dataset.column = column;
        const input = createCellControl(column, rowIndex, row[column]);
        td.appendChild(input);
        tr.appendChild(td);
      });
      fragment.appendChild(tr);
    });
    dom.tbody.appendChild(fragment);
  }

  function createCellControl(column, rowIndex, rawValue) {
    const value = rawValue == null ? "" : String(rawValue);
    let control;

    if (column === "post_id") {
      control = document.createElement("textarea");
      control.className = "cell-control readonly";
      control.readOnly = true;
      control.value = value;
      control.addEventListener("input", () => autoGrowTextarea(control));
      window.requestAnimationFrame(() => autoGrowTextarea(control));
    } else if (BOOLEAN_COLUMNS.has(column)) {
      control = createPickerControl(column, rowIndex, normalizeBooleanValue(value));
    } else if (column === "status") {
      control = createPickerControl(column, rowIndex, normalizeStatusValue(value));
    } else if (column === "upload_date") {
      control = createPickerControl(column, rowIndex, normalizeDateValue(value));
    } else if (column === "upload_time") {
      control = createPickerControl(column, rowIndex, normalizeTimeValue(value));
    } else {
      control = document.createElement("textarea");
      control.className = "cell-control";
      control.value = value;
      control.addEventListener("input", () => autoGrowTextarea(control));
      window.requestAnimationFrame(() => autoGrowTextarea(control));
    }

    if (!control.classList.contains("cell-picker")) {
      control.dataset.row = String(rowIndex);
      control.dataset.column = column;
      control.classList.toggle("modified-field", isRowFieldModified(rowIndex, column));
      control.addEventListener("input", onTableCellChanged);
      control.addEventListener("change", onTableCellChanged);
    }
    return control;
  }

  function createPickerControl(column, rowIndex, value) {
    const wrapper = document.createElement("div");
    wrapper.className = "cell-picker";
    wrapper.dataset.row = String(rowIndex);
    wrapper.dataset.column = column;

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "cell-control cell-picker-trigger";
    trigger.dataset.row = String(rowIndex);
    trigger.dataset.column = column;

    const label = document.createElement("span");
    label.className = "cell-picker-label";
    label.textContent = pickerDisplayValue(column, value);

    const arrow = document.createElement("span");
    arrow.className = "cell-picker-arrow";
    arrow.textContent = "▾";

    trigger.appendChild(label);
    trigger.appendChild(arrow);
    trigger.classList.toggle("modified-field", isRowFieldModified(rowIndex, column));
    if (column === "status") {
      applyStatusTagClass(trigger, value);
    }

    const menu = document.createElement("div");
    menu.className = "cell-picker-menu hidden";

    for (const optionValue of pickerOptionsFor(column)) {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "cell-picker-option";
      option.dataset.value = optionValue;
      option.textContent = pickerDisplayValue(column, optionValue);
      option.classList.toggle("is-selected", optionValue === value);
      if (column === "status") {
        applyStatusTagClass(option, optionValue);
      }
      option.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        applyPickerSelection(wrapper, trigger, menu, column, rowIndex, optionValue);
      });
      menu.appendChild(option);
    }

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleCellPicker(wrapper);
    });

    wrapper.appendChild(trigger);
    wrapper.appendChild(menu);
    return wrapper;
  }

  function applyPickerSelection(wrapper, trigger, menu, column, rowIndex, selectedValue) {
    const oldValue = state.rows[rowIndex][column] == null ? "" : String(state.rows[rowIndex][column]);
    const nextValue = normalizeOnEdit(column, selectedValue);

    for (const option of menu.querySelectorAll(".cell-picker-option")) {
      option.classList.toggle("is-selected", option.dataset.value === selectedValue);
    }

    state.rows[rowIndex][column] = nextValue;
    const label = trigger.querySelector(".cell-picker-label");
    if (label) {
      label.textContent = pickerDisplayValue(column, nextValue);
    }

    if (column === "status") {
      applyStatusTagClass(trigger, nextValue);
    }

    trigger.classList.toggle("modified-field", isRowFieldModified(rowIndex, column));
    closeAllCellPickers();

    if (oldValue !== nextValue) {
      recomputeDirtyState();
      syncButtons();
      updateStatus();
    }
  }

  function toggleCellPicker(wrapper) {
    const menu = wrapper.querySelector(".cell-picker-menu");
    if (!menu) return;
    const isOpen = !menu.classList.contains("hidden");
    closeAllCellPickers();
    if (!isOpen) {
      menu.classList.remove("hidden");
      wrapper.classList.add("is-open");
    }
  }

  function closeAllCellPickers() {
    for (const picker of dom.tbody.querySelectorAll(".cell-picker")) {
      picker.classList.remove("is-open");
      const menu = picker.querySelector(".cell-picker-menu");
      if (menu) {
        menu.classList.add("hidden");
      }
    }
  }

  function pickerOptionsFor(column) {
    if (BOOLEAN_COLUMNS.has(column)) {
      return ["TRUE", "FALSE"];
    }
    if (column === "status") {
      return [...STATUS_VALUES];
    }
    if (column === "upload_date") {
      return buildDateOptionsForMonth(state.month);
    }
    if (column === "upload_time") {
      return buildTimeOptions();
    }
    return [];
  }

  function pickerDisplayValue(column, value) {
    if (!value) {
      if (column === "upload_date") return "Select date";
      if (column === "upload_time") return "Select time";
      return "Select";
    }
    if (BOOLEAN_COLUMNS.has(column)) {
      return value === "TRUE" ? "True" : "False";
    }
    return value;
  }

  function buildDateOptionsForMonth(monthText) {
    const [yearText, monthNumText] = String(monthText || "").split("-");
    const year = Number(yearText);
    const monthNumber = Number(monthNumText);
    if (!year || !monthNumber) return [];
    const daysInMonth = new Date(year, monthNumber, 0).getDate();
    const prefix = `${yearText}-${String(monthNumber).padStart(2, "0")}`;
    const list = [];
    for (let day = 1; day <= daysInMonth; day += 1) {
      list.push(`${prefix}-${String(day).padStart(2, "0")}`);
    }
    return list;
  }

  function buildTimeOptions() {
    const options = [];
    for (let hour = 0; hour < 24; hour += 1) {
      for (let minute = 0; minute < 60; minute += 15) {
        options.push(`${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
      }
    }
    return options;
  }

  function onTableCellChanged(event) {
    const input = event.currentTarget;
    const rowIndex = Number(input.dataset.row);
    const column = input.dataset.column;
    if (!Number.isInteger(rowIndex) || !column) return;

    const oldValue = state.rows[rowIndex][column] == null ? "" : String(state.rows[rowIndex][column]);
    const nextValue = normalizeOnEdit(column, input.value);
    if (oldValue === nextValue) return;

    state.rows[rowIndex][column] = nextValue;
    if (column === "status") {
      applyStatusTagClass(input, nextValue);
    }
    applyCellValidation(input, column, nextValue);
    input.classList.toggle("modified-field", isRowFieldModified(rowIndex, column));
    recomputeDirtyState();
    syncButtons();
    updateStatus();
  }

  function undoLastChange() {
    if (!state.rowsDirty) return;
    state.rows = state.baselineRows.map((row) => ({ ...row }));
    recomputeDirtyState();
    renderTable();
    syncButtons();
    syncInputDirtyUi();
    updateStatus();
  }

  async function generateMonth() {
    if (state.busy) return;

    setBusy(true, "Generating with LLM...");
    try {
      const payload = await window.desktopApi.generatePlansheet(state.month, { input: buildInputPayload() });
      state.exists = true;
      state.rows = Array.isArray(payload.rows) ? payload.rows.map((row) => ({ ...row })) : [];
      state.input = payload.input || buildInputPayload();
      state.columns = Array.isArray(payload.columns) ? payload.columns : [...REQUIRED_COLUMNS];
      state.undoStack = [];
      updateBaselines();
      recomputeDirtyState();
      syncGenerateButtonLabel();
      renderInputForm();
      renderTable();
      syncButtons();
      syncInputDirtyUi();
      updateStatus();
      showToast("Plansheet generated.");
    } catch (error) {
      showToast(`Generate failed: ${error.message}`, "error");
    } finally {
      setBusy(false, "");
    }
  }

  async function saveMonth() {
    if (state.busy) return;

    const validationError = validateRowsStrict();
    if (validationError) {
      showToast(validationError, "error");
      return;
    }

    setBusy(true, "Saving...");
    try {
      const payload = await window.desktopApi.savePlansheet(state.month, {
        columns: state.columns,
        rows: state.rows,
        input: buildInputPayload(),
      });
      state.exists = !!payload.exists;
      state.columns = Array.isArray(payload.columns) ? payload.columns : [...REQUIRED_COLUMNS];
      state.rows = Array.isArray(payload.rows) ? payload.rows.map((row) => ({ ...row })) : [];
      state.input = payload.input || buildInputPayload();
      state.undoStack = [];
      updateBaselines();
      recomputeDirtyState();
      syncGenerateButtonLabel();
      renderInputForm();
      renderTable();
      syncButtons();
      syncInputDirtyUi();
      updateStatus();
      showToast("Saved.");
    } catch (error) {
      showToast(`Save failed: ${error.message}`, "error");
    } finally {
      setBusy(false, "");
    }
  }

  async function removeMonth() {
    if (state.busy || !state.exists) return;
    if (!window.confirm(`Delete plansheet ${state.month}?`)) return;

    setBusy(true, "Removing month...");
    try {
      await window.desktopApi.deletePlansheet(state.month);
      state.exists = false;
      state.rows = [];
      state.undoStack = [];
      updateBaselines();
      recomputeDirtyState();
      syncGenerateButtonLabel();
      renderTable();
      syncButtons();
      syncInputDirtyUi();
      updateStatus();
      showToast("Deleted.");
    } catch (error) {
      showToast(`Delete failed: ${error.message}`, "error");
    } finally {
      setBusy(false, "");
    }
  }

  function buildInputPayload() {
    return {
      ...state.input,
      month: state.month,
      posts_per_week: Number(state.input.posts_per_week || 7),
      target_audience: Array.isArray(state.input.target_audience)
        ? state.input.target_audience
        : [],
    };
  }

  function syncButtons() {
    dom.saveButton.classList.toggle("hidden", !state.dirty);
    dom.removeButton.classList.toggle("hidden", !state.exists);
    dom.undoButton.classList.toggle("hidden", !state.rowsDirty);
  }

  function syncGenerateButtonLabel() {
    dom.generateButton.textContent = state.exists ? "Regenerate" : "Generate";
  }

  function syncInputDirtyUi() {
    dom.saveInputButton.classList.toggle("hidden", !state.inputDirty);
  }

  function updateStatus() {
    const existsText = state.exists ? `${state.rows.length} rows loaded` : "No plansheet yet";
    const dirtyText = state.dirty ? "Unsaved changes" : "Saved";
    setStatus(`Month ${state.month} | ${existsText} | ${dirtyText}`);
  }

  function setStatus(text) {
    dom.statusText.textContent = text;
  }

  function setBusy(isBusy, message) {
    state.busy = isBusy;
    dom.busyText.textContent = message;
    dom.generateButton.disabled = isBusy;
    dom.saveButton.disabled = isBusy;
    dom.removeButton.disabled = isBusy;
    dom.undoButton.disabled = isBusy;
    dom.monthButton.disabled = isBusy;
    dom.toggleInputButton.disabled = isBusy;
    dom.saveInputButton.disabled = isBusy;
  }

  async function selectMonth(nextMonth) {
    if (!nextMonth || !/^\d{4}-\d{2}$/.test(nextMonth)) {
      showToast("Invalid month format", "error");
      return;
    }
    if (nextMonth === state.month) return;
    if (state.dirty && !window.confirm("Unsaved changes will be lost. Continue?")) {
      return;
    }
    state.month = nextMonth;
    state.pickerYear = Number(nextMonth.slice(0, 4));
    await loadMonth();
  }

  function toggleMonthPicker() {
    const isOpen = !dom.monthPicker.classList.contains("hidden");
    if (isOpen) {
      closeMonthPicker();
      return;
    }
    openMonthPicker();
  }

  function openMonthPicker() {
    state.pickerYear = Number(state.month.slice(0, 4));
    renderMonthPicker();
    dom.monthPicker.classList.remove("hidden");
    dom.monthButton.setAttribute("aria-expanded", "true");
  }

  function closeMonthPicker() {
    dom.monthPicker.classList.add("hidden");
    dom.monthButton.setAttribute("aria-expanded", "false");
  }

  function renderMonthPicker() {
    const selectedYear = Number(state.month.slice(0, 4));
    const selectedMonth = state.month.slice(5, 7);
    const current = getCurrentMonth();
    const currentYear = Number(current.slice(0, 4));
    const currentMonth = Number(current.slice(5, 7));
    dom.monthPickerYear.textContent = String(state.pickerYear);

    for (const cell of dom.monthGrid.querySelectorAll(".month-cell")) {
      const month = cell.dataset.month;
      const isSelected = state.pickerYear === selectedYear && month === selectedMonth;
      const monthNumber = Number(month || "0");
      const isPastYear = state.pickerYear < currentYear;
      const isPastMonthInCurrentYear = state.pickerYear === currentYear && monthNumber < currentMonth;
      const isDisabled = isPastYear || isPastMonthInCurrentYear;

      cell.classList.toggle("is-selected", isSelected);
      cell.classList.toggle("is-disabled", isDisabled);
      cell.setAttribute("aria-disabled", isDisabled ? "true" : "false");
      if (isDisabled) {
        cell.setAttribute("tabindex", "-1");
      } else {
        cell.removeAttribute("tabindex");
      }
    }
  }

  function formatMonthLabel(monthValue) {
    const [year, month] = monthValue.split("-");
    const monthIndex = Number(month) - 1;
    const monthName = new Date(Number(year), monthIndex, 1).toLocaleString("en-US", { month: "long" });
    return `${monthName} ${year}`;
  }

  function toggleInputDrawer() {
    const isOpen = document.body.classList.contains("drawer-open");
    if (isOpen) {
      closeInputDrawer();
      return;
    }
    openInputDrawer();
  }

  function openInputDrawer() {
    document.body.classList.add("drawer-open");
    dom.inputDrawer.setAttribute("aria-hidden", "false");
    dom.toggleInputButton.textContent = "Hide Input";
  }

  function closeInputDrawer() {
    document.body.classList.remove("drawer-open");
    dom.inputDrawer.setAttribute("aria-hidden", "true");
    dom.toggleInputButton.textContent = "Generation Input";
  }

  function showToast(message, type = "ok") {
    const node = document.createElement("div");
    node.className = `toast ${type === "error" ? "error" : ""}`;
    node.textContent = message;
    dom.toastHost.appendChild(node);
    setTimeout(() => node.remove(), 3000);
  }

  function autoGrowTextarea(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }

  function normalizeRowsForCompare() {
    return state.rows.map((row) => {
      const normalized = {};
      for (const column of state.columns) {
        const value = row[column];
        normalized[column] = normalizeCellValue(column, value == null ? "" : String(value));
      }
      return normalized;
    });
  }

  function stableStringify(value) {
    if (Array.isArray(value)) {
      return `[${value.map((item) => stableStringify(item)).join(",")}]`;
    }
    if (value && typeof value === "object") {
      const keys = Object.keys(value).sort();
      return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  function currentInputSignature() {
    return stableStringify(buildInputPayload());
  }

  function currentRowsSignature() {
    return stableStringify(normalizeRowsForCompare());
  }

  function updateBaselines() {
    state.baselineRows = normalizeRowsForCompare();
    const baselinePayload = buildInputPayload();
    state.baselineInput = {};
    for (const field of INPUT_FIELDS) {
      state.baselineInput[field.key] = normalizeInputValueForKey(field.key, baselinePayload[field.key]);
    }
    state.baselineInputSig = currentInputSignature();
    state.baselineRowsSig = currentRowsSignature();
  }

  function recomputeDirtyState() {
    const inputChanged = state.baselineInputSig !== currentInputSignature();
    const rowsChanged = state.baselineRowsSig !== currentRowsSignature();
    state.inputDirty = inputChanged;
    state.rowsDirty = rowsChanged;
    state.dirty = inputChanged || rowsChanged;
  }

  function normalizeInputValueForKey(key, value) {
    if (key === "target_audience") {
      if (Array.isArray(value)) {
        return value.map((item) => String(item).trim()).filter(Boolean).join(", ");
      }
      return String(value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
        .join(", ");
    }

    if (key === "posts_per_week") {
      return String(Number(value || 0) || 7);
    }

    return String(value == null ? "" : value);
  }

  function isInputFieldModified(key) {
    const current = normalizeInputValueForKey(key, state.input[key]);
    const baseline = normalizeInputValueForKey(key, state.baselineInput[key]);
    return current !== baseline;
  }

  function isRowFieldModified(rowIndex, key) {
    const currentRow = state.rows[rowIndex] || {};
    const baselineRow = state.baselineRows[rowIndex] || {};
    const current = normalizeCellValue(key, String(currentRow[key] == null ? "" : currentRow[key]));
    const baseline = normalizeCellValue(key, String(baselineRow[key] == null ? "" : baselineRow[key]));
    return current !== baseline;
  }

  function normalizeBooleanValue(value) {
    const text = String(value || "").trim().toLowerCase();
    return text === "true" ? "TRUE" : "FALSE";
  }

  function normalizeStatusValue(value) {
    const text = String(value || "").trim().toUpperCase();
    return STATUS_VALUES.includes(text) ? text : "PLANNED";
  }

  function normalizeDateValue(value) {
    const text = String(value || "").trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : "";
  }

  function normalizeTimeValue(value) {
    const text = String(value || "").trim();
    return /^([01]\d|2[0-3]):[0-5]\d$/.test(text) ? text : "";
  }

  function normalizeCellValue(column, value) {
    if (BOOLEAN_COLUMNS.has(column)) return normalizeBooleanValue(value);
    if (column === "status") return normalizeStatusValue(value);
    if (column === "upload_date") return normalizeDateValue(value);
    if (column === "upload_time") return normalizeTimeValue(value);
    return String(value == null ? "" : value);
  }

  function normalizeOnEdit(column, value) {
    if (BOOLEAN_COLUMNS.has(column)) return normalizeBooleanValue(value);
    if (column === "status") return normalizeStatusValue(value);
    return String(value == null ? "" : value);
  }

  function applyStatusTagClass(control, value) {
    control.classList.remove("status-planned", "status-failed", "status-completed", "status-partially-completed");
    if (value === "PLANNED") control.classList.add("status-planned");
    if (value === "FAILED") control.classList.add("status-failed");
    if (value === "COMPLETED") control.classList.add("status-completed");
    if (value === "PARTIALLY COMPLETED") control.classList.add("status-partially-completed");
  }

  function applyCellValidation(control, column, value) {
    if (column === "upload_date") {
      control.classList.toggle("invalid-field", value !== "" && !/^\d{4}-\d{2}-\d{2}$/.test(value));
      return;
    }
    if (column === "upload_time") {
      control.classList.toggle("invalid-field", value !== "" && !/^([01]\d|2[0-3]):[0-5]\d$/.test(value));
      return;
    }
    control.classList.remove("invalid-field");
  }

  function validateRowsStrict() {
    for (let index = 0; index < state.rows.length; index += 1) {
      const row = state.rows[index];
      const dateValue = normalizeCellValue("upload_date", row.upload_date || "");
      const timeValue = normalizeCellValue("upload_time", row.upload_time || "");
      if (!dateValue) {
        return `Row ${index + 1}: upload_date is required and must be YYYY-MM-DD.`;
      }
      if (!timeValue) {
        return `Row ${index + 1}: upload_time is required and must be HH:mm.`;
      }
    }
    return "";
  }

  init();
})();
