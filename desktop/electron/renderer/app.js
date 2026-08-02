(() => {
  const api = window.desktopApi;
  const DATE_TIME_PATTERN = /^\d{4}-\d{2}-\d{2} ([01]\d|2[0-3]):[0-5]\d$/;
  const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  const state = {
    month: currentMonth(),
    pickerYear: Number(currentMonth().slice(0, 4)),
    inputFields: [],
    rowFields: [],
    sets: [],
    activeSetId: null,
    exists: false,
    rows: [],
    baselineRows: [],
    busy: false,
    editor: null,
  };

  const el = (id) => document.getElementById(id);
  const dom = {
    monthLabel: el("monthLabel"),
    monthButton: el("monthButton"),
    monthPicker: el("monthPicker"),
    monthGrid: el("monthGrid"),
    pickerYear: el("pickerYear"),
    prevYear: el("prevYear"),
    nextYear: el("nextYear"),
    prevMonth: el("prevMonth"),
    nextMonth: el("nextMonth"),
    thisMonth: el("thisMonth"),
    setButton: el("setButton"),
    setLabel: el("setLabel"),
    setMenu: el("setMenu"),
    manageSets: el("manageSets"),
    rowCountChip: el("rowCountChip"),
    dirtyChip: el("dirtyChip"),
    undoButton: el("undoButton"),
    deleteButton: el("deleteButton"),
    saveButton: el("saveButton"),
    generateButton: el("generateButton"),
    emptyGenerate: el("emptyGenerate"),
    emptyState: el("emptyState"),
    tableWrap: el("tableWrap"),
    thead: document.querySelector("#plansheetTable thead"),
    tbody: document.querySelector("#plansheetTable tbody"),
    statusText: el("statusText"),
    busyText: el("busyText"),
    setsOverlay: el("setsOverlay"),
    setsPanel: el("setsPanel"),
    closeSets: el("closeSets"),
    setsList: el("setsList"),
    setForm: el("setForm"),
    newSet: el("newSet"),
    saveSet: el("saveSet"),
    deleteSet: el("deleteSet"),
    setFormHint: el("setFormHint"),
    dialogHost: el("dialogHost"),
    dialogTitle: el("dialogTitle"),
    dialogBody: el("dialogBody"),
    dialogConfirm: el("dialogConfirm"),
    dialogCancel: el("dialogCancel"),
    toastHost: el("toastHost"),
  };

  /* ------------------------------ bootstrap ------------------------------ */

  async function init() {
    buildMonthGrid();
    bindEvents();
    try {
      await api.health();
      const meta = await api.getMeta();
      state.inputFields = meta.input_fields;
      state.rowFields = meta.row_fields;
      state.sets = await api.listInputSets();
      await loadMonth();
    } catch (error) {
      setStatus(`Backend unavailable: ${error.message}`);
      toast(`Backend unavailable: ${error.message}`, "error");
    }
  }

  async function loadMonth() {
    setBusy("Loading");
    try {
      applyPlansheet(await api.getPlansheet(state.month));
    } catch (error) {
      toast(`Load failed: ${error.message}`, "error");
    } finally {
      setBusy("");
    }
  }

  function applyPlansheet(payload) {
    state.exists = payload.exists;
    state.rows = payload.rows.map((row) => ({ ...row }));
    state.baselineRows = payload.rows.map((row) => ({ ...row }));
    state.activeSetId = payload.input_set_id;
    renderAll();
  }

  function renderAll() {
    dom.monthLabel.textContent = monthLabel(state.month);
    dom.setLabel.textContent = activeSet()?.name || "No input set";
    renderTable();
    syncChrome();
  }

  /* -------------------------------- state -------------------------------- */

  function activeSet() {
    return state.sets.find((set) => set.id === state.activeSetId) || state.sets[0] || null;
  }

  function isDirty() {
    return JSON.stringify(state.rows) !== JSON.stringify(state.baselineRows);
  }

  function isCellModified(rowIndex, key) {
    const baseline = state.baselineRows[rowIndex];
    if (!baseline) return false;
    return String(state.rows[rowIndex][key] ?? "") !== String(baseline[key] ?? "");
  }

  function syncChrome() {
    const dirty = isDirty();
    dom.rowCountChip.textContent = state.exists ? `${state.rows.length} posts` : "No plansheet";
    dom.dirtyChip.classList.toggle("hidden", !dirty);
    dom.saveButton.classList.toggle("hidden", !dirty);
    dom.undoButton.classList.toggle("hidden", !dirty);
    dom.deleteButton.classList.toggle("hidden", !state.exists);
    dom.generateButton.textContent = state.exists ? "Regenerate" : "Generate";
    setStatus(`${monthLabel(state.month)} · ${activeSet()?.name || "no input set"} · ${dirty ? "unsaved changes" : "saved"}`);
  }

  function setStatus(text) {
    dom.statusText.textContent = text;
  }

  function setBusy(message) {
    state.busy = Boolean(message);
    dom.busyText.textContent = message;
    const buttons = [
      dom.generateButton, dom.saveButton, dom.deleteButton, dom.undoButton, dom.emptyGenerate,
      dom.setButton, dom.monthButton, dom.saveSet, dom.newSet,
    ];
    for (const button of buttons) button.disabled = state.busy;
    syncSetButtons();
  }

  function syncSetButtons() {
    const soleSet = state.sets.length <= 1;
    dom.deleteSet.disabled = state.busy || soleSet;
    dom.deleteSet.title = soleSet ? "At least one input set must exist" : "";
  }

  /* -------------------------------- table -------------------------------- */

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

    const headRow = document.createElement("tr");
    headRow.appendChild(createElement("th", { className: "col-index", textContent: "#" }));
    for (const field of state.rowFields) {
      headRow.appendChild(createElement("th", { textContent: field.label, dataset: { key: field.key } }));
    }
    dom.thead.appendChild(headRow);

    const fragment = document.createDocumentFragment();
    state.rows.forEach((row, rowIndex) => {
      const tr = document.createElement("tr");
      tr.appendChild(createElement("td", { className: "col-index", textContent: String(rowIndex + 1) }));
      for (const field of state.rowFields) {
        const td = createElement("td", { dataset: { key: field.key } });
        td.appendChild(createCell(field, rowIndex, String(row[field.key] ?? "")));
        tr.appendChild(td);
      }
      fragment.appendChild(tr);
    });
    dom.tbody.appendChild(fragment);
  }

  function createCell(field, rowIndex, value) {
    if (field.type === "readonly") {
      return createElement("div", { className: "cell-static", textContent: value, title: value });
    }
    if (field.type === "select") {
      return createSelectCell(field, rowIndex, value);
    }
    if (field.type === "datetime") {
      return createDateTimeCell(rowIndex, value);
    }

    const control = field.type === "textarea"
      ? createElement("textarea", { className: "cell-text", value })
      : createElement("input", { className: "cell-input", type: "text", value });

    control.classList.toggle("is-modified", isCellModified(rowIndex, field.key));
    control.addEventListener("input", () => {
      if (field.type === "textarea") autoGrow(control);
      commitCell(control, field.key, rowIndex, control.value);
    });

    if (field.type === "textarea") {
      requestAnimationFrame(() => autoGrow(control));
    }
    return control;
  }

  function createSelectCell(field, rowIndex, value) {
    const wrapper = createElement("div", { className: "cell-picker" });
    const trigger = createElement("button", { className: "cell-trigger", type: "button" });
    const label = createElement("span", { className: "label", textContent: value || "Select" });
    trigger.append(label, createElement("span", { className: "caret" }));
    trigger.classList.toggle("is-empty", !value);
    trigger.classList.toggle("is-modified", isCellModified(rowIndex, field.key));
    applyTag(label, value);

    const menu = createElement("div", { className: "cell-menu hidden" });
    for (const option of field.options) {
      const button = createElement("button", { className: "cell-option dot-tag", type: "button", textContent: option });
      applyTag(button, option);
      button.classList.toggle("is-selected", option === value);
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        label.textContent = option;
        trigger.classList.remove("is-empty");
        applyTag(label, option);
        for (const sibling of menu.children) sibling.classList.toggle("is-selected", sibling.textContent === option);
        closeCellMenus();
        commitCell(trigger, field.key, rowIndex, option);
      });
      menu.appendChild(button);
    }

    label.classList.add("dot-tag");
    menu.addEventListener("click", (event) => event.stopPropagation());
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleCellMenu(trigger, menu);
    });
    wrapper.append(trigger, menu);
    return wrapper;
  }

  function createDateTimeCell(rowIndex, value) {
    const wrapper = createElement("div", { className: "cell-picker" });
    const trigger = createElement("button", { className: "cell-trigger", type: "button" });
    const label = createElement("span", { className: "label", textContent: value || "Set date & time" });
    trigger.append(label, createElement("span", { className: "caret" }));
    trigger.classList.toggle("is-empty", !value);
    trigger.classList.toggle("is-modified", isCellModified(rowIndex, "date_time"));
    trigger.classList.toggle("is-invalid", !DATE_TIME_PATTERN.test(value));

    const menu = createElement("div", { className: "cell-menu dt-menu hidden" });
    menu.addEventListener("click", (event) => event.stopPropagation());
    const view = { date: "", time: "18:00", year: 0, month: 0 };

    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const willOpen = menu.classList.contains("hidden");
      closeCellMenus();
      if (!willOpen) return;

      const parsed = DATE_TIME_PATTERN.test(label.textContent) ? label.textContent : "";
      const [datePart, timePart] = parsed ? parsed.split(" ") : [`${state.month}-01`, "18:00"];
      view.date = parsed ? datePart : "";
      view.time = timePart;
      view.year = Number(datePart.slice(0, 4));
      view.month = Number(datePart.slice(5, 7));
      renderCalendar();
      openCellMenu(trigger, menu);
    });

    function renderCalendar() {
      menu.innerHTML = "";

      const head = createElement("div", { className: "picker-head" });
      const prev = createElement("button", { className: "icon-btn icon-btn-sm", type: "button", innerHTML: "&#8249;" });
      const next = createElement("button", { className: "icon-btn icon-btn-sm", type: "button", innerHTML: "&#8250;" });
      const title = createElement("span", {
        className: "picker-title",
        textContent: `${MONTH_NAMES[view.month - 1]} ${view.year}`,
      });
      prev.addEventListener("click", (event) => {
        event.stopPropagation();
        shiftView(-1);
      });
      next.addEventListener("click", (event) => {
        event.stopPropagation();
        shiftView(1);
      });
      head.append(prev, title, next);

      const weekdays = createElement("div", { className: "dt-weekdays" });
      for (const day of ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]) {
        weekdays.appendChild(createElement("span", { textContent: day }));
      }

      const days = createElement("div", { className: "dt-days" });
      const offset = (new Date(view.year, view.month - 1, 1).getDay() + 6) % 7;
      for (let gap = 0; gap < offset; gap += 1) days.appendChild(createElement("span"));

      const total = new Date(view.year, view.month, 0).getDate();
      for (let day = 1; day <= total; day += 1) {
        const iso = `${pad(view.year, 4)}-${pad(view.month)}-${pad(day)}`;
        const button = createElement("button", { className: "dt-day", type: "button", textContent: String(day) });
        button.classList.toggle("is-selected", iso === view.date);
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          view.date = iso;
          renderCalendar();
        });
        days.appendChild(button);
      }

      const timeRow = createElement("div", { className: "dt-time" });
      const hour = createElement("input", { type: "text", maxLength: 2, value: view.time.slice(0, 2) });
      const minute = createElement("input", { type: "text", maxLength: 2, value: view.time.slice(3, 5) });
      const apply = createElement("button", { className: "btn btn-accent btn-sm", type: "button", textContent: "Apply" });
      apply.addEventListener("click", (event) => {
        event.stopPropagation();
        if (!view.date) return;
        const next = `${view.date} ${clampTime(hour.value, 23)}:${clampTime(minute.value, 59)}`;
        label.textContent = next;
        trigger.classList.remove("is-empty", "is-invalid");
        closeCellMenus();
        commitCell(trigger, "date_time", rowIndex, next);
      });
      timeRow.append(hour, createElement("span", { className: "sep", textContent: ":" }), minute, apply);

      menu.append(head, weekdays, days, timeRow);

      // Month lengths change the grid height, so re-anchor after every redraw.
      if (!menu.classList.contains("hidden")) positionCellMenu(trigger, menu);
    }

    function shiftView(delta) {
      const shifted = new Date(view.year, view.month - 1 + delta, 1);
      view.year = shifted.getFullYear();
      view.month = shifted.getMonth() + 1;
      renderCalendar();
    }

    wrapper.append(trigger, menu);
    return wrapper;
  }

  function commitCell(control, key, rowIndex, value) {
    state.rows[rowIndex][key] = value;
    control.classList.toggle("is-modified", isCellModified(rowIndex, key));
    syncChrome();
  }

  function applyTag(node, value) {
    node.classList.remove("tag-planned", "tag-failed", "tag-completed", "tag-partially-completed", "tag-true", "tag-false");
    if (value) node.classList.add(`tag-${value.toLowerCase().replace(/\s+/g, "-")}`);
  }

  function toggleCellMenu(trigger, menu) {
    const willOpen = menu.classList.contains("hidden");
    closeCellMenus();
    if (willOpen) openCellMenu(trigger, menu);
  }

  function openCellMenu(trigger, menu) {
    menu.classList.remove("hidden");
    positionCellMenu(trigger, menu);
  }

  // Anchors the fixed menu to its trigger, flipping above and clamping sideways
  // so it never lands outside the window.
  function positionCellMenu(trigger, menu) {
    const gap = 4;
    const margin = 8;
    const anchor = trigger.getBoundingClientRect();

    if (!menu.classList.contains("dt-menu")) {
      menu.style.minWidth = `${anchor.width}px`;
    }

    const { offsetWidth: width, offsetHeight: height } = menu;

    let top = anchor.bottom + gap;
    if (top + height > window.innerHeight - margin) {
      const above = anchor.top - height - gap;
      top = above >= margin ? above : Math.max(margin, window.innerHeight - height - margin);
    }

    let left = anchor.left;
    if (left + width > window.innerWidth - margin) left = window.innerWidth - width - margin;

    menu.style.top = `${top}px`;
    menu.style.left = `${Math.max(margin, left)}px`;
  }

  function closeCellMenus() {
    for (const menu of dom.tbody.querySelectorAll(".cell-menu")) menu.classList.add("hidden");
  }

  /* ------------------------------- actions ------------------------------- */

  async function generate() {
    if (state.busy) return;
    if (!activeSet()) {
      toast("Create an input set first.", "error");
      return;
    }
    if (state.exists && !(await confirmDialog("Regenerate month?", "The current rows for this month will be replaced by a fresh generation."))) {
      return;
    }

    setBusy("Generating with LLM");
    try {
      applyPlansheet(await api.generatePlansheet(state.month, state.activeSetId));
      toast(`Generated ${state.rows.length} posts.`);
    } catch (error) {
      toast(`Generate failed: ${error.message}`, "error");
    } finally {
      setBusy("");
    }
  }

  async function save() {
    if (state.busy) return;

    const invalid = state.rows.findIndex((row) => !DATE_TIME_PATTERN.test(String(row.date_time ?? "")));
    if (invalid !== -1) {
      toast(`Row ${invalid + 1}: date_time must be YYYY-MM-DD HH:mm.`, "error");
      return;
    }

    setBusy("Saving");
    try {
      applyPlansheet(await api.savePlansheet(state.month, { input_set_id: state.activeSetId, rows: state.rows }));
      toast("Saved.");
    } catch (error) {
      toast(`Save failed: ${error.message}`, "error");
    } finally {
      setBusy("");
    }
  }

  async function removeMonth() {
    if (state.busy || !state.exists) return;
    if (!(await confirmDialog("Delete plansheet?", `All ${state.rows.length} posts for ${monthLabel(state.month)} will be removed.`))) {
      return;
    }

    setBusy("Deleting");
    try {
      await api.deletePlansheet(state.month);
      await loadMonth();
      toast("Plansheet deleted.");
    } catch (error) {
      toast(`Delete failed: ${error.message}`, "error");
    } finally {
      setBusy("");
    }
  }

  function undo() {
    state.rows = state.baselineRows.map((row) => ({ ...row }));
    renderTable();
    syncChrome();
  }

  async function selectMonth(month) {
    if (month === state.month) return;
    if (isDirty() && !(await confirmDialog("Discard changes?", "Unsaved edits to this month will be lost."))) {
      return;
    }
    state.month = month;
    state.pickerYear = Number(month.slice(0, 4));
    closePopovers();
    await loadMonth();
  }

  async function chooseSet(setId) {
    closePopovers();
    if (setId === state.activeSetId) return;
    state.activeSetId = setId;
    dom.setLabel.textContent = activeSet()?.name || "No input set";
    syncChrome();
    if (!state.exists) return;

    try {
      await api.selectInputSet(state.month, setId);
    } catch (error) {
      toast(`Could not switch input set: ${error.message}`, "error");
    }
  }

  /* ----------------------------- input sets ------------------------------ */

  function openSetsPanel() {
    closePopovers();
    dom.setsOverlay.classList.remove("hidden");
    dom.setsPanel.classList.remove("hidden");
    dom.setsPanel.setAttribute("aria-hidden", "false");
    loadEditor(activeSet());
  }

  function closeSetsPanel() {
    dom.setsOverlay.classList.add("hidden");
    dom.setsPanel.classList.add("hidden");
    dom.setsPanel.setAttribute("aria-hidden", "true");
    state.editor = null;
  }

  function loadEditor(set) {
    const values = {};
    for (const field of state.inputFields) {
      values[field.key] = set ? set[field.key] : (field.type === "int" ? 1 : field.type === "bool" ? 0 : "");
    }
    state.editor = { setId: set ? set.id : null, values, baseline: JSON.stringify(values) };
    renderSetsList();
    renderSetForm();
  }

  function editorDirty() {
    return Boolean(state.editor) && JSON.stringify(state.editor.values) !== state.editor.baseline;
  }

  function renderSetsList() {
    dom.setsList.innerHTML = "";
    for (const set of state.sets) {
      const item = createElement("button", { className: "set-item", type: "button" });
      item.appendChild(createElement("span", { className: "name", textContent: set.name }));
      if (set.id === state.activeSetId) {
        item.appendChild(createElement("span", { className: "badge", textContent: "IN USE" }));
      }
      item.classList.toggle("is-active", state.editor?.setId === set.id);
      item.addEventListener("click", () => void switchEditor(set));
      dom.setsList.appendChild(item);
    }

    if (state.editor && state.editor.setId === null) {
      const draft = createElement("button", { className: "set-item is-active is-draft", type: "button" });
      draft.appendChild(createElement("span", { className: "name", textContent: state.editor.values.name || "New set" }));
      draft.appendChild(createElement("span", { className: "badge", textContent: "DRAFT" }));
      dom.setsList.appendChild(draft);
    }
  }

  async function switchEditor(set) {
    if (editorDirty() && !(await confirmDialog("Discard set changes?", "The edits to this input set have not been saved."))) {
      return;
    }
    loadEditor(set);
  }

  function renderSetForm() {
    dom.setForm.innerHTML = "";
    dom.setFormHint.textContent = editorDirty() ? "Unsaved" : "";
    dom.deleteSet.classList.toggle("hidden", state.editor.setId === null);
    dom.saveSet.textContent = state.editor.setId === null ? "Create set" : "Save set";
    syncSetButtons();

    for (const field of state.inputFields) {
      const row = createElement("div", { className: "form-row" });
      if (field.type === "textarea" || field.key === "name") row.classList.add("span-2");
      row.appendChild(createElement("label", { textContent: field.label }));
      row.appendChild(createSetControl(field));
      dom.setForm.appendChild(row);
    }
  }

  function createSetControl(field) {
    const value = state.editor.values[field.key];

    if (field.type === "bool") {
      const wrapper = createElement("label", { className: "switch" });
      const checkbox = createElement("input", { type: "checkbox", checked: Boolean(value) });
      const track = createElement("span", { className: "track" });
      track.appendChild(createElement("span", { className: "thumb" }));
      const text = createElement("span", { className: "switch-text", textContent: value ? "Yes" : "No" });
      checkbox.addEventListener("change", () => {
        text.textContent = checkbox.checked ? "Yes" : "No";
        onEditorChange(field.key, checkbox.checked ? 1 : 0);
      });
      wrapper.append(checkbox, track, text);
      return wrapper;
    }

    if (field.type === "textarea") {
      const control = createElement("textarea", { value: String(value ?? "") });
      control.addEventListener("input", () => onEditorChange(field.key, control.value));
      return control;
    }

    const control = createElement("input", {
      type: field.type === "int" ? "number" : "text",
      value: String(value ?? ""),
    });
    if (field.type === "int") control.min = "1";
    control.addEventListener("input", () => {
      onEditorChange(field.key, field.type === "int" ? Number(control.value || 0) : control.value);
    });
    return control;
  }

  function onEditorChange(key, value) {
    state.editor.values[key] = value;
    dom.setFormHint.textContent = editorDirty() ? "Unsaved" : "";
    if (key === "name") renderSetsList();
  }

  async function saveEditor() {
    const values = state.editor.values;
    if (!String(values.name || "").trim()) {
      toast("Set name is required.", "error");
      return;
    }

    setBusy("Saving input set");
    try {
      const saved = state.editor.setId === null
        ? await api.createInputSet(values)
        : await api.updateInputSet(state.editor.setId, values);
      state.sets = await api.listInputSets();
      if (state.editor.setId === null) state.activeSetId = saved.id;
      loadEditor(state.sets.find((set) => set.id === saved.id));
      dom.setLabel.textContent = activeSet()?.name || "No input set";
      syncChrome();
      toast(`Input set "${saved.name}" saved.`);
    } catch (error) {
      toast(`Could not save input set: ${error.message}`, "error");
    } finally {
      setBusy("");
    }
  }

  async function deleteEditor() {
    const set = state.sets.find((item) => item.id === state.editor.setId);
    if (!set) return;
    if (!(await confirmDialog("Delete input set?", `"${set.name}" will be removed. Months generated with it keep their rows.`))) {
      return;
    }

    setBusy("Deleting input set");
    try {
      await api.deleteInputSet(set.id);
      state.sets = await api.listInputSets();
      if (state.activeSetId === set.id) state.activeSetId = state.sets[0]?.id ?? null;
      loadEditor(activeSet());
      dom.setLabel.textContent = activeSet()?.name || "No input set";
      syncChrome();
      toast("Input set deleted.");
    } catch (error) {
      toast(`Could not delete input set: ${error.message}`, "error");
    } finally {
      setBusy("");
    }
  }

  function newSetDraft() {
    const source = state.sets.find((set) => set.id === state.editor?.setId) || activeSet();
    const values = {};
    for (const field of state.inputFields) {
      values[field.key] = source ? source[field.key] : (field.type === "int" ? 1 : field.type === "bool" ? 0 : "");
    }
    values.name = uniqueSetName(source ? `${source.name} copy` : "New set");
    state.editor = { setId: null, values, baseline: "" };
    renderSetsList();
    renderSetForm();
    dom.setForm.querySelector("input")?.focus();
  }

  function uniqueSetName(base) {
    const taken = new Set(state.sets.map((set) => set.name));
    if (!taken.has(base)) return base;
    let counter = 2;
    while (taken.has(`${base} ${counter}`)) counter += 1;
    return `${base} ${counter}`;
  }

  /* ------------------------------ popovers ------------------------------- */

  function buildMonthGrid() {
    dom.monthGrid.innerHTML = "";
    MONTH_NAMES.forEach((name, index) => {
      const cell = createElement("button", { className: "month-cell", type: "button", textContent: name });
      cell.dataset.month = pad(index + 1);
      cell.addEventListener("click", () => void selectMonth(`${state.pickerYear}-${pad(index + 1)}`));
      dom.monthGrid.appendChild(cell);
    });
  }

  function renderMonthPicker() {
    dom.pickerYear.textContent = String(state.pickerYear);
    const [selectedYear, selectedMonth] = state.month.split("-");
    const [nowYear, nowMonth] = currentMonth().split("-");
    for (const cell of dom.monthGrid.children) {
      cell.classList.toggle("is-selected", Number(selectedYear) === state.pickerYear && cell.dataset.month === selectedMonth);
      cell.classList.toggle("is-current", Number(nowYear) === state.pickerYear && cell.dataset.month === nowMonth);
    }
  }

  function renderSetMenu() {
    dom.setMenu.innerHTML = "";
    for (const set of state.sets) {
      const option = createElement("button", { className: "set-option", type: "button" });
      option.appendChild(createElement("span", { textContent: set.name }));
      if (set.id === state.activeSetId) option.appendChild(createElement("span", { className: "tick", textContent: "✓" }));
      option.classList.toggle("is-selected", set.id === state.activeSetId);
      option.addEventListener("click", () => void chooseSet(set.id));
      dom.setMenu.appendChild(option);
    }
    if (state.sets.length === 0) {
      dom.setMenu.appendChild(createElement("div", { className: "set-option", textContent: "No input sets" }));
    }
  }

  function togglePopover(node, render) {
    const willOpen = node.classList.contains("hidden");
    closePopovers();
    if (!willOpen) return;
    render();
    node.classList.remove("hidden");
  }

  function closePopovers() {
    dom.monthPicker.classList.add("hidden");
    dom.setMenu.classList.add("hidden");
    dom.monthButton.setAttribute("aria-expanded", "false");
    dom.setButton.setAttribute("aria-expanded", "false");
  }

  /* ------------------------- dialog, toast, utils ------------------------ */

  function confirmDialog(title, body) {
    dom.dialogTitle.textContent = title;
    dom.dialogBody.textContent = body;
    dom.dialogHost.classList.remove("hidden");

    return new Promise((resolve) => {
      const finish = (result) => {
        dom.dialogHost.classList.add("hidden");
        dom.dialogConfirm.removeEventListener("click", onConfirm);
        dom.dialogCancel.removeEventListener("click", onCancel);
        resolve(result);
      };
      const onConfirm = () => finish(true);
      const onCancel = () => finish(false);
      dom.dialogConfirm.addEventListener("click", onConfirm);
      dom.dialogCancel.addEventListener("click", onCancel);
    });
  }

  function toast(message, type = "ok") {
    const node = createElement("div", { className: `toast ${type === "error" ? "error" : ""}`, textContent: message });
    dom.toastHost.appendChild(node);
    setTimeout(() => node.remove(), 4000);
  }

  function createElement(tag, props = {}) {
    const node = document.createElement(tag);
    const { dataset, ...rest } = props;
    Object.assign(node, rest);
    if (dataset) Object.assign(node.dataset, dataset);
    return node;
  }

  function autoGrow(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }

  function pad(value, size = 2) {
    return String(value).padStart(size, "0");
  }

  function clampTime(text, max) {
    const parsed = Number.parseInt(String(text).replace(/\D/g, ""), 10);
    return pad(Number.isNaN(parsed) ? 0 : Math.min(max, Math.max(0, parsed)));
  }

  function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  }

  function monthLabel(month) {
    const [year, index] = month.split("-");
    return `${new Date(Number(year), Number(index) - 1, 1).toLocaleString("en-US", { month: "long" })} ${year}`;
  }

  function shiftMonth(month, delta) {
    const [year, index] = month.split("-").map(Number);
    const shifted = new Date(year, index - 1 + delta, 1);
    return `${shifted.getFullYear()}-${pad(shifted.getMonth() + 1)}`;
  }

  /* ------------------------------- events -------------------------------- */

  function bindEvents() {
    dom.monthButton.addEventListener("click", (event) => {
      event.stopPropagation();
      state.pickerYear = Number(state.month.slice(0, 4));
      togglePopover(dom.monthPicker, renderMonthPicker);
      dom.monthButton.setAttribute("aria-expanded", String(!dom.monthPicker.classList.contains("hidden")));
    });
    dom.setButton.addEventListener("click", (event) => {
      event.stopPropagation();
      togglePopover(dom.setMenu, renderSetMenu);
      dom.setButton.setAttribute("aria-expanded", String(!dom.setMenu.classList.contains("hidden")));
    });
    dom.prevYear.addEventListener("click", (event) => {
      event.stopPropagation();
      state.pickerYear -= 1;
      renderMonthPicker();
    });
    dom.nextYear.addEventListener("click", (event) => {
      event.stopPropagation();
      state.pickerYear += 1;
      renderMonthPicker();
    });
    dom.thisMonth.addEventListener("click", () => void selectMonth(currentMonth()));
    dom.prevMonth.addEventListener("click", () => void selectMonth(shiftMonth(state.month, -1)));
    dom.nextMonth.addEventListener("click", () => void selectMonth(shiftMonth(state.month, 1)));

    dom.generateButton.addEventListener("click", () => void generate());
    dom.emptyGenerate.addEventListener("click", () => void generate());
    dom.saveButton.addEventListener("click", () => void save());
    dom.deleteButton.addEventListener("click", () => void removeMonth());
    dom.undoButton.addEventListener("click", undo);

    dom.manageSets.addEventListener("click", openSetsPanel);
    dom.closeSets.addEventListener("click", () => void closeSetsPanelSafely());
    dom.setsOverlay.addEventListener("click", () => void closeSetsPanelSafely());
    dom.newSet.addEventListener("click", () => void newSetDraft());
    dom.saveSet.addEventListener("click", () => void saveEditor());
    dom.deleteSet.addEventListener("click", () => void deleteEditor());

    for (const node of [dom.monthPicker, dom.setMenu, dom.setsPanel]) {
      node.addEventListener("click", (event) => event.stopPropagation());
    }

    document.addEventListener("click", () => {
      closePopovers();
      closeCellMenus();
    });

    // A fixed menu would drift away from its cell, so dismiss it instead.
    dom.tableWrap.addEventListener("scroll", closeCellMenus, { passive: true });
    window.addEventListener("resize", () => {
      closeCellMenus();
      closePopovers();
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closePopovers();
        closeCellMenus();
        if (!dom.setsPanel.classList.contains("hidden")) void closeSetsPanelSafely();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void save();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z" && isDirty()) {
        event.preventDefault();
        undo();
      }
    });
  }

  async function closeSetsPanelSafely() {
    if (editorDirty() && !(await confirmDialog("Discard set changes?", "The edits to this input set have not been saved."))) {
      return;
    }
    closeSetsPanel();
  }

  init();
})();
