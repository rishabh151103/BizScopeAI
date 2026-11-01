const $ = (selector) => document.querySelector(selector);

const ui = {
  sidebar: $("#sidebar"),
  conversationList: $("#conversation-list"),
  search: $("#conversation-search"),
  welcome: $("#welcome"),
  thread: $("#message-thread"),
  threadScroll: $("#thread-scroll"),
  input: $("#message-input"),
  send: $("#send-message"),
  typing: $("#typing-row"),
  file: $("#file-input"),
  dialog: $("#confirm-dialog"),
};

const storageKeys = {
  datasetId: "bizscope.defaultDatasetId",
  conversationId: "bizscope.activeConversationId",
  titles: "bizscope.conversationTitles",
};

const state = {
  conversations: [],
  investigationId: null,
  messages: [],
  datasetId: readNumber(storageKeys.datasetId),
  datasetInfo: null,
  activeDatasetId: null,
  activeDatasetInfo: null,
  legacyVisualizations: {},
  busy: false,
  streamingResponse: null,
  streamingStatus: "",
  editingIndex: null,
  renameMap: readJson(storageKeys.titles, {}),
  pendingQuestion: "",
};

function readNumber(key) {
  const value = Number(localStorage.getItem(key));
  return Number.isInteger(value) && value > 0 ? value : null;
}

function readJson(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch { return fallback; }
}

function saveLocalState() {
  if (state.datasetId) localStorage.setItem(storageKeys.datasetId, String(state.datasetId));
  else localStorage.removeItem(storageKeys.datasetId);
  if (state.investigationId) localStorage.setItem(storageKeys.conversationId, String(state.investigationId));
  else localStorage.removeItem(storageKeys.conversationId);
  localStorage.setItem(storageKeys.titles, JSON.stringify(state.renameMap));
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch { /* keep the status message */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

async function streamChat(options, onEvent) {
  const response = await fetch("/chat/stream", options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch { /* keep the status message */ }
    throw new Error(message);
  }
  if (!response.body) throw new Error("This browser cannot stream the response.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  const consumeFrame = (frame) => {
    const data = frame.split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;
    const event = JSON.parse(data);
    if (event.type === "error") throw new Error(event.detail || "The chat request failed.");
    if (event.type === "done") result = event.result;
    onEvent(event);
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      const frames = buffer.split("\n\n");
      buffer = frames.pop() || "";
      for (const frame of frames) consumeFrame(frame);
      if (done) break;
    }
    if (buffer.trim()) consumeFrame(buffer);
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  }
  if (!result) throw new Error("The server ended the response before completing it.");
  return result;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function renderInline(text) {
  let output = escapeHtml(text);
  output = output.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  output = output.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  output = output.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  return output;
}

function renderMarkdown(markdown) {
  const lines = String(markdown ?? "").replace(/\r/g, "").split("\n");
  const blocks = [];
  let paragraph = [];
  let list = [];
  let listKind = "";
  let table = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(`<p>${paragraph.map(renderInline).join("<br>")}</p>`);
      paragraph = [];
    }
  };
  const flushList = () => {
    if (!list.length) return;
    const tag = listKind === "ol" ? "ol" : "ul";
    blocks.push(`<${tag}>${list.map((item) => `<li>${renderInline(item)}</li>`).join("")}</${tag}>`);
    list = [];
    listKind = "";
  };
  const flushTable = () => {
    if (!table.length) return;
    const rows = table.map((line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()));
    const meaningful = rows.filter((row) => !row.every((cell) => /^:?-{3,}:?$/.test(cell)));
    if (meaningful.length) {
      const [head, ...body] = meaningful;
      blocks.push(`<div class="markdown-table-scroll"><table><thead><tr>${head.map((cell) => `<th>${renderInline(cell)}</th>`).join("")}</tr></thead><tbody>${body.map((row) => `<tr>${head.map((_, index) => `<td>${renderInline(row[index] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
    }
    table = [];
  };

  for (const line of lines) {
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    const unordered = line.match(/^\s*[-*•]\s+(.+)$/);
    if (/^\s*\|.+\|?\s*$/.test(line) && line.includes("|")) {
      flushParagraph(); flushList(); table.push(line);
    } else if (!line.trim() && table.length) {
      flushTable();
    } else if (heading) {
      flushTable();
      flushParagraph(); flushList();
      const level = Math.min(heading[1].length + 1, 4);
      blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
    } else if (ordered || unordered) {
      flushTable();
      flushParagraph();
      const kind = ordered ? "ol" : "ul";
      if (listKind && listKind !== kind) flushList();
      listKind = kind;
      list.push((ordered || unordered)[1]);
    } else if (/^\s*>/.test(line)) {
      flushTable();
      flushParagraph(); flushList();
      blocks.push(`<blockquote>${renderInline(line.replace(/^\s*>\s?/, ""))}</blockquote>`);
    } else if (/^\s*---+\s*$/.test(line)) {
      flushTable();
      flushParagraph(); flushList(); blocks.push("<hr>");
    } else if (!line.trim()) {
      flushTable();
      flushParagraph(); flushList();
    } else {
      flushTable();
      flushList(); paragraph.push(line);
    }
  }
  flushTable(); flushParagraph(); flushList();
  return blocks.join("");
}

function toast(message, isError = false) {
  const node = document.createElement("div");
  node.className = `toast${isError ? " error" : ""}`;
  node.textContent = message;
  $("#toast-region").append(node);
  window.setTimeout(() => node.remove(), 3800);
}

function formatRelativeTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "";
  const seconds = Math.max(0, (Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

function activeTitle() {
  if (!state.investigationId) return "New investigation";
  const item = state.conversations.find((conversation) => conversation.investigation_id === state.investigationId);
  return state.renameMap[state.investigationId] || item?.title || "Business investigation";
}

function updateDatasetDisplay() {
  const isActiveConversation = Boolean(state.investigationId);
  const info = isActiveConversation ? state.activeDatasetInfo : state.datasetInfo;
  $("#dataset-name").textContent = info?.filename || "No dataset selected";
  $("#dataset-meta").textContent = info
    ? `${Number(info.rows || 0).toLocaleString()} rows · ${info.columns ?? "—"} columns${isActiveConversation ? " · this investigation" : " · ready to use"}`
    : (isActiveConversation ? "This investigation has no dataset" : "Upload a CSV to get started");
  $("#composer-hint").textContent = info ? "Ask, explore, follow the evidence" : "You can begin with a business question";
}

function renderConversationList() {
  const query = ui.search.value.trim().toLowerCase();
  const visible = state.conversations.filter((item) => {
    const title = state.renameMap[item.investigation_id] || item.title || "Business investigation";
    return title.toLowerCase().includes(query);
  });
  ui.conversationList.replaceChildren();
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty-history";
    empty.textContent = query ? "No matching investigations." : "Your investigations will appear here.";
    ui.conversationList.append(empty);
    return;
  }
  for (const item of visible) {
    const button = document.createElement("button");
    button.className = `conversation-item${item.investigation_id === state.investigationId ? " active" : ""}`;
    button.type = "button";
    button.title = item.title || "Business investigation";
    button.innerHTML = `<span class="history-icon" aria-hidden="true">◷</span><span class="conversation-title"></span><span class="conversation-date"></span>`;
    button.querySelector(".conversation-title").textContent = state.renameMap[item.investigation_id] || item.title || "Business investigation";
    button.querySelector(".conversation-date").textContent = formatRelativeTime(item.updated_at);
    button.addEventListener("click", () => loadConversation(item.investigation_id));
    ui.conversationList.append(button);
  }
}

async function loadConversations() {
  const data = await api("/investigations");
  state.conversations = data.conversations || [];
  renderConversationList();
}

async function loadDataset(datasetId) {
  if (!datasetId) return null;
  try { return await api(`/datasets/${datasetId}`); }
  catch { return null; }
}

async function loadConversation(investigationId) {
  try {
    const details = await api(`/investigations/${investigationId}`);
    state.investigationId = details.investigation_id;
    state.messages = details.messages || [];
    state.activeDatasetId = details.dataset_id || null;
    state.activeDatasetInfo = await loadDataset(state.activeDatasetId);
    state.legacyVisualizations = details.visualizations_by_assistant_index || {};
    state.editingIndex = null;
    saveLocalState();
    renderAll();
    closeSidebarOnMobile();
  } catch (error) {
    toast(`Could not open investigation: ${error.message}`, true);
  }
}

function newConversation() {
  state.investigationId = null;
  state.messages = [];
  state.activeDatasetId = null;
  state.activeDatasetInfo = null;
  state.legacyVisualizations = {};
  state.editingIndex = null;
  state.pendingQuestion = "";
  saveLocalState();
  renderAll();
  ui.input.focus();
  closeSidebarOnMobile();
}

function renderAll() {
  $("#topbar-title").textContent = activeTitle();
  $("#delete-conversation").classList.toggle("hidden", !state.investigationId);
  $("#rename-conversation").classList.toggle("hidden", !state.investigationId);
  $("#edit-branch-banner").classList.toggle("hidden", state.editingIndex === null);
  $("#welcome").classList.toggle("hidden", state.messages.length > 0 || Boolean(state.pendingQuestion));
  updateDatasetDisplay();
  renderConversationList();
  renderMessages();
}

function openChartDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("bizscope-local-ui", 2);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("charts")) {
        db.createObjectStore("charts", { keyPath: "key" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function saveCharts(investigationId, assistantIndex, charts) {
  if (!investigationId || !charts?.length) return false;
  try {
    const db = await openChartDb();
    await new Promise((resolve, reject) => {
      const transaction = db.transaction("charts", "readwrite");
      transaction.objectStore("charts").put({ key: `${investigationId}:${assistantIndex}`, charts });
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
    });
    db.close();
    return true;
  } catch {
    state.legacyVisualizations[String(assistantIndex)] = charts;
    return false;
  }
}

async function getCharts(investigationId, assistantIndex) {
  if (!investigationId) return [];
  try {
    const db = await openChartDb();
    const result = await new Promise((resolve, reject) => {
      const request = db.transaction("charts").objectStore("charts").get(`${investigationId}:${assistantIndex}`);
      request.onsuccess = () => resolve(request.result?.charts || []);
      request.onerror = () => reject(request.error);
    });
    db.close();
    return result.length ? result : (state.legacyVisualizations[String(assistantIndex)] || []);
  } catch { return state.legacyVisualizations[String(assistantIndex)] || []; }
}

function createMessageAction(label, symbol, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-action";
  button.textContent = `${symbol} ${label}`;
  button.addEventListener("click", handler);
  return button;
}

async function copyText(value, label) {
  try {
    await navigator.clipboard.writeText(value || "");
    toast(`${label} copied`);
  } catch { toast("Clipboard access is unavailable in this browser.", true); }
}

function renderMessageEditor(message, index) {
  const form = document.createElement("div");
  const editor = document.createElement("textarea");
  editor.className = "edit-box";
  editor.value = message.content || "";
  editor.setAttribute("aria-label", "Edit this message");
  const actions = document.createElement("div");
  actions.className = "edit-actions";
  const cancel = document.createElement("button");
  cancel.className = "secondary-button";
  cancel.textContent = "Cancel";
  cancel.addEventListener("click", () => { state.editingIndex = null; renderAll(); });
  const send = document.createElement("button");
  send.className = "primary-button";
  send.textContent = "Continue from here";
  send.addEventListener("click", () => {
    const editedText = editor.value.trim();
    if (editedText) sendMessage(editedText, { branchFromIndex: index });
  });
  actions.append(cancel, send);
  form.append(editor, actions);
  return form;
}

function renderMessages() {
  ui.thread.replaceChildren();
  let assistantIndex = 0;
  state.messages.forEach((message, index) => {
    if (!message || !["user", "assistant"].includes(message.role)) return;
    if (message.role === "assistant") assistantIndex += 1;
    const row = document.createElement("article");
    row.className = `message-row ${message.role}`;
    const avatar = document.createElement("div");
    avatar.className = message.role === "assistant" ? "assistant-avatar" : "user-avatar";
    avatar.textContent = message.role === "assistant" ? "B" : "You";
    const content = document.createElement("div");
    content.className = "message-content";
    const author = document.createElement("div");
    author.className = "message-author";
    author.innerHTML = message.role === "assistant" ? "BizScopeAI" : "You";
    content.append(author);

    if (message.role === "user" && state.editingIndex === index) {
      content.append(renderMessageEditor(message, index));
    } else if (message.role === "user") {
      const bubble = document.createElement("div");
      bubble.className = "user-bubble";
      bubble.textContent = message.content || "";
      content.append(bubble);
      const actions = document.createElement("div");
      actions.className = "message-actions";
      actions.append(createMessageAction("Edit", "✎", () => {
        state.editingIndex = index;
        renderAll();
        ui.thread.querySelector(".edit-box")?.focus();
      }));
      actions.append(createMessageAction("Copy", "▢", async () => {
        await copyText(message.content, "Message");
      }));
      content.append(actions);
    } else {
      const body = document.createElement("div");
      body.className = "assistant-body";
      body.innerHTML = renderMarkdown(message.content || "");
      content.append(body);
      const actions = document.createElement("div");
      actions.className = "message-actions";
      actions.append(createMessageAction("Copy", "▢", async () => {
        await copyText(message.content, "Response");
      }));
      const previousUser = state.messages.slice(0, index).map((item, i) => ({ item, i })).reverse().find(({ item }) => item.role === "user");
      if (previousUser) actions.append(createMessageAction("Try again", "↻", () => sendMessage(previousUser.item.content, { branchFromIndex: previousUser.i })));
      content.append(actions);
      getCharts(state.investigationId, assistantIndex).then((charts) => {
        if (!charts.length || !window.Plotly || !row.isConnected) return;
        for (const chart of charts) {
          const chartNode = document.createElement("div");
          chartNode.className = "chart-wrap";
          chartNode.style.minHeight = "300px";
          content.append(chartNode);
          try {
            const figure = typeof chart === "string" ? JSON.parse(chart) : chart;
            window.Plotly.newPlot(chartNode, figure.data || [], figure.layout || {}, { responsive: true, displaylogo: false });
          } catch { chartNode.textContent = "This saved chart could not be displayed."; }
        }
      });
    }
    row.append(avatar, content);
    ui.thread.append(row);
  });
  if (state.pendingQuestion) {
    const row = document.createElement("article");
    row.className = "message-row user pending-message";
    row.innerHTML = `<div class="user-avatar">You</div><div class="message-content"><div class="message-author">You</div></div>`;
    const bubble = document.createElement("div");
    bubble.className = "user-bubble";
    bubble.textContent = state.pendingQuestion;
    row.querySelector(".message-content").append(bubble);
    ui.thread.append(row);
  }
  if (state.streamingResponse !== null) {
    const row = document.createElement("article");
    row.className = "message-row assistant streaming-message-row";
    const avatar = document.createElement("div");
    avatar.className = "assistant-avatar";
    avatar.textContent = "B";
    const content = document.createElement("div");
    content.className = "message-content";
    const author = document.createElement("div");
    author.className = "message-author";
    author.textContent = "BizScopeAI";
    const status = document.createElement("div");
    status.className = "streaming-status";
    status.textContent = state.streamingStatus || "Preparing the response…";
    const body = document.createElement("div");
    body.className = "assistant-body streaming-body";
    body.innerHTML = state.streamingResponse
      ? `${renderMarkdown(state.streamingResponse)}<span class="streaming-cursor" aria-hidden="true"></span>`
      : "<p>Checking the available evidence…</p>";
    content.append(author, status, body);
    row.append(avatar, content);
    ui.thread.append(row);
  }
  ui.welcome.classList.toggle("hidden", state.messages.length > 0 || Boolean(state.pendingQuestion));
  window.requestAnimationFrame(() => { ui.threadScroll.scrollTop = ui.threadScroll.scrollHeight; });
}

function setBusy(value) {
  state.busy = value;
  ui.send.disabled = value;
  ui.input.disabled = value;
  ui.typing.classList.toggle("hidden", !value);
  ui.input.placeholder = value ? "BizScopeAI is investigating…" : "Ask a business question…";
  if (value) window.requestAnimationFrame(() => { ui.threadScroll.scrollTop = ui.threadScroll.scrollHeight; });
}

async function sendMessage(message = ui.input.value, options = {}) {
  const prompt = String(message || "").trim();
  if (!prompt || state.busy) return;
  const branchFromIndex = options.branchFromIndex;
  const isBranch = Number.isInteger(branchFromIndex);
  const branchContext = isBranch
    ? state.messages.slice(0, branchFromIndex).filter((item) => ["user", "assistant"].includes(item.role)).slice(-16).map(({ role, content }) => ({ role, content: String(content || "").slice(-2000) }))
    : [];
  const datasetId = state.investigationId ? state.activeDatasetId : state.datasetId;
  const previousConversationId = state.investigationId;
  state.pendingQuestion = prompt;
  state.streamingResponse = "";
  state.streamingStatus = "Checking the available evidence…";
  state.editingIndex = null;
  $("#edit-branch-banner").classList.add("hidden");
  ui.input.value = "";
  autoSizeInput();
  setBusy(true);
  renderMessages();

  try {
    const result = await streamChat({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: prompt,
        investigation_id: isBranch ? null : state.investigationId,
        dataset_id: datasetId,
        branch_context: branchContext,
      }),
      signal: AbortSignal.timeout(600_000),
    }, (event) => {
      if (event.type === "status") {
        state.streamingStatus = event.message || "Working…";
        const status = ui.thread.querySelector(".streaming-status");
        if (status) status.textContent = state.streamingStatus;
      } else if (event.type === "token") {
        state.streamingResponse += event.text || "";
        const body = ui.thread.querySelector(".streaming-body");
        if (body) {
          body.innerHTML = `${renderMarkdown(state.streamingResponse)}<span class="streaming-cursor" aria-hidden="true"></span>`;
          ui.threadScroll.scrollTop = ui.threadScroll.scrollHeight;
        }
      }
    });
    const newId = result.investigation_id ?? state.investigationId;
    if (newId) {
      if (newId !== previousConversationId) state.legacyVisualizations = {};
      state.investigationId = newId;
      state.activeDatasetId = datasetId;
      state.activeDatasetInfo = datasetId ? (await loadDataset(datasetId)) : null;
      const details = await api(`/investigations/${newId}`);
      state.messages = details.messages || [];
      const assistantCount = state.messages.filter((item) => item.role === "assistant").length;
      await saveCharts(newId, assistantCount, result.visualizations || []);
      await loadConversations();
      if (isBranch && previousConversationId) {
        const branchTitle = `Edited: ${prompt}`.slice(0, 90);
        state.renameMap[newId] = branchTitle;
      }
      saveLocalState();
    } else {
      state.messages = [...state.messages, { role: "user", content: prompt }, { role: "assistant", content: result.response || "I couldn't generate a response." }];
    }
    state.pendingQuestion = "";
    state.streamingResponse = null;
    state.streamingStatus = "";
    setBusy(false);
    renderAll();
    if (result.visualizations?.length && !newId) toast("The answer is ready; its chart could not be attached to a saved conversation.");
    if (isBranch) toast("Created a new conversation branch from your edit.");
  } catch (error) {
    state.pendingQuestion = "";
    state.streamingResponse = null;
    state.streamingStatus = "";
    setBusy(false);
    renderMessages();
    ui.input.value = prompt;
    autoSizeInput();
    toast(error.name === "TimeoutError" ? "This investigation is taking longer than expected. Check the conversation before retrying." : error.message, true);
  }
}

function autoSizeInput() {
  ui.input.style.height = "auto";
  ui.input.style.height = `${Math.min(ui.input.scrollHeight, 180)}px`;
}

async function uploadDataset(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".csv")) {
    toast("Choose a CSV file.", true);
    return;
  }
  const form = new FormData();
  form.append("file", file, file.name);
  $("#connection-label").textContent = "Uploading dataset…";
  try {
    const result = await api("/datasets/upload", { method: "POST", body: form, signal: AbortSignal.timeout(120_000) });
    state.datasetId = result.dataset_id;
    state.datasetInfo = result;
    saveLocalState();
    updateDatasetDisplay();
    toast(`Added ${result.filename}. It’s ready for your next investigation.`);
  } catch (error) {
    toast(`Dataset upload failed: ${error.message}`, true);
  } finally {
    await checkConnection();
    ui.file.value = "";
  }
}

async function checkConnection() {
  const dot = $("#connection-dot");
  const label = $("#connection-label");
  try {
    await api("/health/ready", { signal: AbortSignal.timeout(5000) });
    dot.style.background = "#6fbc87";
    label.textContent = "Local engine connected";
    label.parentElement.classList.remove("offline");
  } catch {
    dot.style.background = "#df8179";
    label.textContent = "Backend unavailable";
    label.parentElement.classList.add("offline");
  }
}

function openConfirm({ title, description, confirmLabel = "Continue", danger = false }) {
  return new Promise((resolve) => {
    $("#dialog-title").textContent = title;
    $("#dialog-description").textContent = description;
    $("#dialog-confirm").textContent = confirmLabel;
    $("#dialog-confirm").classList.toggle("danger", danger);
    ui.dialog.addEventListener("close", function handler() {
      ui.dialog.removeEventListener("close", handler);
      resolve(ui.dialog.returnValue === "confirm");
    }, { once: true });
    ui.dialog.showModal();
  });
}

async function deleteConversation() {
  if (!state.investigationId) return;
  const confirmed = await openConfirm({
    title: "Delete this investigation?",
    description: "This permanently removes its conversation and saved analysis from the local database.",
    confirmLabel: "Delete investigation",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await api(`/investigations/${state.investigationId}`, { method: "DELETE" });
    delete state.renameMap[state.investigationId];
    newConversation();
    await loadConversations();
    toast("Investigation deleted.");
  } catch (error) { toast(`Could not delete investigation: ${error.message}`, true); }
}

async function renameConversation() {
  if (!state.investigationId) return;
  const current = activeTitle();
  const next = window.prompt("Name this investigation", current);
  if (next === null) return;
  const title = next.trim().slice(0, 90);
  if (!title) { toast("Please enter a name.", true); return; }
  state.renameMap[state.investigationId] = title;
  saveLocalState();
  renderAll();
}

function closeSidebarOnMobile() {
  if (window.matchMedia("(max-width: 650px)").matches) ui.sidebar.classList.remove("open");
}

function setupEvents() {
  $("#new-chat").addEventListener("click", newConversation);
  $("#refresh-conversations").addEventListener("click", () => loadConversations().catch((error) => toast(error.message, true)));
  $("#upload-dataset").addEventListener("click", () => ui.file.click());
  $("#composer-upload").addEventListener("click", () => ui.file.click());
  ui.file.addEventListener("change", () => uploadDataset(ui.file.files?.[0]));
  ui.search.addEventListener("input", renderConversationList);
  ui.input.addEventListener("input", autoSizeInput);
  ui.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); }
  });
  ui.send.addEventListener("click", () => sendMessage());
  $("#delete-conversation").addEventListener("click", deleteConversation);
  $("#rename-conversation").addEventListener("click", renameConversation);
  $("#open-sidebar").addEventListener("click", () => ui.sidebar.classList.add("open"));
  $("#close-sidebar").addEventListener("click", closeSidebarOnMobile);
  $("#cancel-edit").addEventListener("click", () => { state.editingIndex = null; renderAll(); });
  document.querySelectorAll(".suggestion-card").forEach((card) => card.addEventListener("click", () => {
    ui.input.value = card.dataset.prompt || "";
    autoSizeInput();
    ui.input.focus();
  }));
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); newConversation(); }
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) { event.preventDefault(); ui.search.focus(); }
    if (event.key === "Escape") { state.editingIndex = null; renderMessages(); closeSidebarOnMobile(); }
  });
}

async function initialize() {
  setupEvents();
  renderAll();
  checkConnection();
  try {
    if (state.datasetId) state.datasetInfo = await loadDataset(state.datasetId);
    await loadConversations();
    const savedId = readNumber(storageKeys.conversationId);
    if (savedId && state.conversations.some((item) => item.investigation_id === savedId)) {
      await loadConversation(savedId);
    } else {
      saveLocalState();
      renderAll();
    }
  } catch (error) {
    toast(`Could not load local workspace: ${error.message}`, true);
  }
}

initialize();
