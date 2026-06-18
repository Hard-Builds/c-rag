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
async function loadThreads() {
  const threads = await apiFetch("/private/thread/");
  setState({ threads: threads ?? [] });
  renderThreadList();
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

  const label = document.createElement("div");
  label.className = "msg-label";
  label.textContent = role === "human" ? "You" : "Bot";

  const text = document.createElement("div");
  if (role === "ai") {
    text.className = "msg-markdown";
    text.innerHTML = marked.parse(content);
  } else {
    text.textContent = content;
  }

  wrap.appendChild(label);
  wrap.appendChild(text);
  return wrap;
}

function scrollToBottom() {
  const container = document.getElementById("messages-container");
  container.scrollTop = container.scrollHeight;
}

// ── Send message ──────────────────────────────────────────
async function sendMessage(query) {
  // Determine thread — generate UUID client-side for new threads
  const isNewThread = !state.activeThreadId;
  const threadId = state.activeThreadId ?? crypto.randomUUID();

  // Optimistically show the human message
  const humanMsg = { id: crypto.randomUUID(), role: "human", content: query };
  setState({ messages: [...state.messages, humanMsg], isLoading: true });
  showChatPanel();
  renderMessages();
  setInputLocked(true);
  document.getElementById("loading-indicator").hidden = false;

  try {
    const answer = await apiFetch(
      `/private/thread/${threadId}/query?query=${encodeURIComponent(query)}`,
      { method: "POST" }
    );

    const aiMsg = { id: crypto.randomUUID(), role: "ai", content: answer };
    setState({
      activeThreadId: threadId,
      messages: [...state.messages, aiMsg],
      isLoading: false,
    });
    renderMessages();

    if (isNewThread) {
      // Refresh sidebar so the new thread appears with its LLM-generated title
      await loadThreads();
      renderThreadList();
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
    await apiFetch("/private/ingest/", { method: "POST", body: formData });
    showUploadStatus("Document uploaded and indexed successfully.", "success");
    document.getElementById("file-label-text").textContent = "Choose a PDF file";
    fileInput.value = "";
    setTimeout(closeModal, 1800);
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

  // Upload modal open
  document.getElementById("upload-btn").addEventListener("click", openModal);

  // Modal close buttons
  document.getElementById("modal-close-btn").addEventListener("click", closeModal);
  document.getElementById("upload-cancel-btn").addEventListener("click", closeModal);

  // Backdrop click closes modal
  document.querySelector(".modal-backdrop").addEventListener("click", closeModal);

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
    await loadThreads();
  } catch (err) {
    console.error("Failed to load threads:", err);
  }
}

document.addEventListener("DOMContentLoaded", init);
