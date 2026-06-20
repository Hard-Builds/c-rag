// ── Config ────────────────────────────────────────────────
const CONFIG = {
  BASE_URL: "/api/v1",
  TOKEN: "dev-token", // backend ignores token value for now
};

// ── State ─────────────────────────────────────────────────
const state = {
  threads: [],          // [{ id, title }, ...]
  activeThreadId: null, // UUID string | null
  messages: [],         // [{ id, role, content }, ...]
  isLoading: false,
};

function setState(patch) {
  Object.assign(state, patch);
}

// ── API helper ────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = {
    Authorization: `Bearer ${CONFIG.TOKEN}`,
    ...options.headers,
  };
  const res = await fetch(CONFIG.BASE_URL + path, { ...options, headers });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  const json = await res.json();
  return json.payload;
}

// ── Thread list ───────────────────────────────────────────
async function loadThreads({ preservePlaceholders = false } = {}) {
  const threads = await apiFetch("/private/thread/");
  const fetched = threads ?? [];
  if (preservePlaceholders) {
    const localMap = Object.fromEntries(state.threads.map(t => [t.id, t]));
    const merged = fetched.map(t => (!t.title && localMap[t.id]) ? { ...t, title: localMap[t.id].title } : t);
    setState({ threads: merged });
  } else {
    setState({ threads: fetched });
  }
  renderThreadList();
}

function renderThreadListSkeleton(count = 3) {
  const list = document.getElementById("thread-list");
  list.innerHTML = "";
  for (let i = 0; i < count; i++) {
    const li = document.createElement("li");
    li.className = "thread-skeleton";
    li.innerHTML = `<span class="skeleton-line" style="width:${55 + Math.random() * 30}%"></span>`;
    list.appendChild(li);
  }
}

function renderThreadList() {
  const list = document.getElementById("thread-list");
  list.innerHTML = "";
  for (const thread of state.threads) {
    const li = document.createElement("li");
    li.innerHTML = marked.parseInline(thread.title || "Untitled");
    li.dataset.id = thread.id;
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", thread.id === state.activeThreadId ? "true" : "false");
    if (thread.id === state.activeThreadId) li.classList.add("active");
    li.addEventListener("click", () => selectThread(thread.id));
    list.appendChild(li);
  }
}

async function selectThread(threadId) {
  setState({ activeThreadId: threadId, messages: [] });
  history.pushState({}, "", `/chat/${threadId}`);
  renderThreadList();
  showChatPanel();
  await loadMessages(threadId);
}

// ── Messages ──────────────────────────────────────────────
async function loadMessages(threadId) {
  const messages = await apiFetch(`/private/thread/${threadId}/`);
  setState({ messages: messages ?? [] });
  renderMessages();
}

function renderMessages() {
  const container = document.getElementById("messages-container");
  container.innerHTML = "";
  for (const msg of state.messages) {
    container.appendChild(createBubble(msg.role, msg.content));
  }
  scrollToBottom();
}

function createBubble(role, content) {
  const wrap = document.createElement("div");
  wrap.className = role === "human" ? "msg msg-human" : "msg msg-ai";

  const inner = document.createElement("div");
  inner.className = "msg-content";

  if (role === "ai") {
    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = "rag";
    wrap.appendChild(label);
    inner.className = "msg-content msg-markdown";
    inner.innerHTML = marked.parse(content);
  } else {
    inner.textContent = content;
  }

  wrap.appendChild(inner);
  return wrap;
}

function scrollToBottom() {
  const container = document.getElementById("messages-container");
  container.scrollTop = container.scrollHeight;
}

// ── Send message ──────────────────────────────────────────
async function sendMessage(query) {
  const isNewThread = !state.activeThreadId;
  const threadId = state.activeThreadId ?? crypto.randomUUID();

  const humanMsg = { id: crypto.randomUUID(), role: "human", content: query };
  setState({ messages: [...state.messages, humanMsg], isLoading: true, activeThreadId: threadId });
  showChatPanel();

  if (isNewThread) {
    setState({ threads: [{ id: threadId, title: query.slice(0, 40) }, ...state.threads] });
    renderThreadList();
  }

  renderMessages();
  setInputLocked(true);
  document.getElementById("loading-indicator").hidden = false;

  try {
    const res = await fetch(
      `${CONFIG.BASE_URL}/private/thread/${threadId}/query`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${CONFIG.TOKEN}`,
        },
        body: JSON.stringify({ query }),
      }
    );

    if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);

    const aiMsg = { id: crypto.randomUUID(), role: "ai", content: "" };
    setState({ messages: [...state.messages, aiMsg] });
    renderMessages();

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      aiMsg.content += decoder.decode(value, { stream: true });
      const bubbles = document.querySelectorAll(".msg-ai .msg-markdown");
      if (bubbles.length) {
        bubbles[bubbles.length - 1].innerHTML = marked.parse(aiMsg.content);
        scrollToBottom();
      }
    }

    setState({ isLoading: false });

    if (isNewThread) {
      setTimeout(() => loadThreads({ preservePlaceholders: true }), 3000);
    }
  } catch (err) {
    const errMsg = { id: crypto.randomUUID(), role: "ai", content: `Error: ${err.message}` };
    setState({ messages: [...state.messages, errMsg], isLoading: false });
    renderMessages();
  } finally {
    document.getElementById("loading-indicator").hidden = true;
    setInputLocked(false);
    document.getElementById("query-input").focus();
  }
}

// ── Docs modal ────────────────────────────────────────────
function openDocsModal() {
  document.getElementById("docs-modal").hidden = false;
  loadDocuments();
}

function closeDocsModal() {
  document.getElementById("docs-modal").hidden = true;
}

async function loadDocuments() {
  const tbody = document.getElementById("docs-tbody");
  const table = document.getElementById("docs-table");
  const empty = document.getElementById("docs-empty");
  const statusEl = document.getElementById("docs-list-status");

  tbody.innerHTML = "";
  table.hidden = true;
  empty.hidden = true;
  statusEl.hidden = true;

  try {
    const docs = await apiFetch("/private/document/");
    if (!docs || docs.length === 0) {
      empty.hidden = false;
      return;
    }
    for (const doc of docs) {
      const fmtDate = (iso) => new Date(iso).toLocaleString(undefined, {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      });

      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${doc.filename}</td><td>${fmtDate(doc.uploaded_at)}</td><td>${fmtDate(doc.updated_at)}</td><td></td><td></td><td></td>`;

      const statusTd = tr.querySelectorAll("td")[3];
      const badge = document.createElement("span");
      badge.className = `status-badge status-badge--${doc.status}`;
      badge.textContent = doc.status;
      statusTd.appendChild(badge);

      if (doc.error) {
        const truncated = doc.error.length > 32 ? doc.error.slice(0, 32) + "…" : doc.error;
        const errSpan = document.createElement("span");
        errSpan.className = "doc-error-inline";
        errSpan.textContent = truncated;
        errSpan.title = doc.error;
        tr.querySelectorAll("td")[4].appendChild(errSpan);
      }

      const deleteBtn = document.createElement("button");
      deleteBtn.className = "btn-delete";
      deleteBtn.textContent = "Delete";
      deleteBtn.addEventListener("click", () => deleteDocument(doc.id, tr, deleteBtn));
      tr.querySelector("td:last-child").appendChild(deleteBtn);

      tbody.appendChild(tr);
    }
    table.hidden = false;
  } catch (err) {
    statusEl.textContent = `Failed to load documents: ${err.message}`;
    statusEl.className = "upload-status error";
    statusEl.hidden = false;
  }
}

async function deleteDocument(id, rowEl, btnEl) {
  if (!confirm("Delete this document?")) return;
  btnEl.disabled = true;
  try {
    await apiFetch(`/private/document/?document_id=${id}`, { method: "DELETE" });
    rowEl.remove();
    const tbody = document.getElementById("docs-tbody");
    if (!tbody.children.length) {
      document.getElementById("docs-table").hidden = true;
      document.getElementById("docs-empty").hidden = false;
    }
  } catch (err) {
    alert(`Delete failed: ${err.message}`);
    btnEl.disabled = false;
  }
}

// ── Upload modal ──────────────────────────────────────────
function openModal() {
  const modal = document.getElementById("upload-modal");
  modal.hidden = false;
  resetModal();
}

function closeModal() {
  document.getElementById("upload-modal").hidden = true;
}

function resetModal() {
  document.getElementById("file-input").value = "";
  document.getElementById("file-label-text").textContent = "Choose a PDF file";
  const status = document.getElementById("upload-status");
  status.hidden = true;
  status.className = "upload-status";
  status.textContent = "";
  document.getElementById("upload-confirm-btn").disabled = false;
}

async function uploadFile() {
  const fileInput = document.getElementById("file-input");
  const statusEl = document.getElementById("upload-status");

  if (!fileInput.files.length) {
    showUploadStatus("Please select a PDF file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  document.getElementById("upload-confirm-btn").disabled = true;
  showUploadStatus("Uploading and processing...", "loading");

  try {
    await apiFetch("/private/document/ingest", { method: "POST", body: formData });
    showUploadStatus("Document uploaded successfully.", "success");
    document.getElementById("file-label-text").textContent = "Choose a PDF file";
    fileInput.value = "";
    setTimeout(() => { closeModal(); openDocsModal(); }, 1800);
  } catch (err) {
    showUploadStatus(`Upload failed: ${err.message}`, "error");
    document.getElementById("upload-confirm-btn").disabled = false;
  }
}

function showUploadStatus(text, type) {
  const el = document.getElementById("upload-status");
  el.textContent = text;
  el.className = `upload-status ${type}`;
  el.hidden = false;
}

// ── UI helpers ────────────────────────────────────────────
function showChatPanel() {
  document.getElementById("empty-state").style.display = "none";
  document.getElementById("messages-container").style.display = "flex";
}

function showEmptyState() {
  document.getElementById("empty-state").style.display = "flex";
  document.getElementById("messages-container").style.display = "none";
}

function setInputLocked(locked) {
  document.getElementById("query-input").disabled = locked;
  document.getElementById("send-btn").disabled = locked;
}

// ── Event wiring ──────────────────────────────────────────
function wireEvents() {
  // New chat
  document.getElementById("new-chat-btn").addEventListener("click", () => {
    setState({ activeThreadId: null, messages: [] });
    history.pushState({}, "", "/");
    renderThreadList();
    showEmptyState();
    document.getElementById("query-input").value = "";
    document.getElementById("query-input").focus();
  });

  // Send message
  document.getElementById("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("query-input");
    const query = input.value.trim();
    if (!query || state.isLoading) return;
    input.value = "";
    await sendMessage(query);
  });

  // Upload modal
  document.getElementById("upload-btn").addEventListener("click", openModal);
  document.getElementById("modal-close-btn").addEventListener("click", closeModal);
  document.getElementById("upload-cancel-btn").addEventListener("click", closeModal);

  // Docs modal
  document.getElementById("docs-btn").addEventListener("click", openDocsModal);
  document.getElementById("docs-modal-close-btn").addEventListener("click", closeDocsModal);
  document.getElementById("docs-modal-close-footer-btn").addEventListener("click", closeDocsModal);
  document.getElementById("docs-refresh-btn").addEventListener("click", loadDocuments);
  document.getElementById("docs-add-btn").addEventListener("click", () => { closeDocsModal(); openModal(); });

  // Backdrop click closes the right modal
  document.querySelectorAll(".modal-backdrop").forEach((el) => {
    el.addEventListener("click", () => {
      const modalId = el.dataset.closes;
      if (modalId) document.getElementById(modalId).hidden = true;
    });
  });

  // File picker label update
  document.getElementById("file-input").addEventListener("change", (e) => {
    const name = e.target.files[0]?.name ?? "Choose a PDF file";
    document.getElementById("file-label-text").textContent = name;
  });

  // Upload confirm
  document.getElementById("upload-confirm-btn").addEventListener("click", uploadFile);
}

// ── Init ──────────────────────────────────────────────────
async function init() {
  wireEvents();
  showEmptyState();

  try {
    renderThreadListSkeleton(4);
    await loadThreads();
  } catch (err) {
    console.error("Failed to load threads:", err);
  }

  const match = window.location.pathname.match(/\/chat\/([a-f0-9-]{36})/);
  if (match) {
    await selectThread(match[1]);
  }
}

document.addEventListener("DOMContentLoaded", init);
