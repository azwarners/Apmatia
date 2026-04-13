const conversationEl = document.getElementById("conversation");
const statusEl = document.getElementById("status");
const sendButtonEl = document.getElementById("send-button");
const resetButtonEl = document.getElementById("reset-button");
const promptEl = document.getElementById("prompt");
const scrollLatestButtonEl = document.getElementById("scroll-latest-button");
const discussionBottomEl = document.getElementById("discussion-bottom");

let pollHandle = null;
let userLabel = "User";
let followLiveEdge = true;

function setStatus(text) {
  statusEl.innerText = text;
}

function autoGrowPrompt() {
  promptEl.style.height = "auto";
  promptEl.style.height = `${promptEl.scrollHeight}px`;
  syncBottomInset();
}

function isNearBottom() {
  return conversationEl.scrollTop + conversationEl.clientHeight >= conversationEl.scrollHeight - 24;
}

function pageIsNearBottom() {
  const pageBottom = window.scrollY + window.innerHeight;
  return pageBottom >= document.documentElement.scrollHeight - 24;
}

function updateScrollLatestVisibility() {
  if (!scrollLatestButtonEl) {
    return;
  }
  const conversationCanScroll = conversationEl.scrollHeight > conversationEl.clientHeight + 24;
  const pageCanScroll = document.documentElement.scrollHeight > window.innerHeight + 24;
  const shouldShow = (conversationCanScroll || pageCanScroll) && (!isNearBottom() || !pageIsNearBottom());
  scrollLatestButtonEl.classList.toggle("is-visible", shouldShow);
}

function syncBottomInset() {
  if (!discussionBottomEl) {
    return;
  }
  const inset = Math.ceil(discussionBottomEl.getBoundingClientRect().height) + 16;
  document.documentElement.style.setProperty("--discussion-bottom-height", `${inset}px`);
  updateScrollLatestVisibility();
}

function atLiveEdge() {
  return isNearBottom() && pageIsNearBottom();
}

function scrollConversationToBottom(behavior = "auto") {
  followLiveEdge = true;
  conversationEl.scrollTo({ top: conversationEl.scrollHeight, behavior });
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior });
  updateScrollLatestVisibility();
}

function closeMobileDrawer() {
  document.body.classList.remove("mobile-menu-open");
}

function toDisplayName(username) {
  const clean = String(username || "").trim();
  if (!clean) {
    return "User";
  }
  const firstToken = clean.split(/[\s._-]+/)[0] || clean;
  return firstToken.charAt(0).toUpperCase() + firstToken.slice(1);
}

async function loadUserLabel() {
  try {
    const response = await fetch("/api/auth/session");
    if (!response.ok) {
      return;
    }
    const session = await response.json();
    userLabel = toDisplayName(session.username);
  } catch (error) {
    // Keep fallback label when session lookup fails.
  }
}

function renderConversation(messages) {
  const fragment = document.createDocumentFragment();
  const normalized = Array.isArray(messages) ? messages : [];

  if (normalized.length === 0) {
    conversationEl.innerHTML = "";
    return;
  }

  normalized.forEach((message) => {
    const role = message?.role === "User" ? "User" : "Assistant";
    const text = String(message?.text || "").trimEnd();
    if (!text) {
      return;
    }

    const item = document.createElement("article");
    item.className = `chat-message ${role === "User" ? "from-user" : "from-assistant"}`;

    const label = document.createElement("div");
    label.className = "chat-label";
    label.textContent = role === "User" ? `${userLabel}:` : "Assistant:";

    const body = document.createElement("div");
    body.className = "chat-body";
    body.textContent = text;

    item.appendChild(label);
    item.appendChild(body);
    fragment.appendChild(item);
  });

  conversationEl.innerHTML = "";
  conversationEl.appendChild(fragment);
}

function renderSnapshot(snapshot) {
  renderConversation(snapshot.messages || []);

  if (followLiveEdge) {
    scrollConversationToBottom();
  } else {
    updateScrollLatestVisibility();
  }

  if (snapshot.is_streaming) {
    setStatus("Streaming response...");
    sendButtonEl.disabled = true;
    if (resetButtonEl) {
      resetButtonEl.disabled = true;
    }
  } else {
    setStatus(snapshot.last_error ? `Error: ${snapshot.last_error}` : "Idle");
    sendButtonEl.disabled = false;
    if (resetButtonEl) {
      resetButtonEl.disabled = false;
    }
  }
}

async function fetchSnapshot() {
  try {
    const response = await fetch("/api/discussion/state");
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const snapshot = await response.json();
    renderSnapshot(snapshot);
  } catch (error) {
    setStatus("Connection lost. Retrying...");
  }
}

async function sendPrompt() {
  const prompt = (promptEl.value || "").trim();
  if (!prompt) {
    setStatus("Please enter a prompt.");
    return;
  }

  try {
    followLiveEdge = true;
    const response = await fetch("/api/discussion/prompt", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      const err = await response.json();
      setStatus(`Unable to start: ${err.detail || response.statusText}`);
      return;
    }
    promptEl.value = "";
    autoGrowPrompt();
    await fetchSnapshot();
  } catch (error) {
    setStatus("Failed to send prompt.");
  }
}

async function resetDiscussion() {
  try {
    const response = await fetch("/api/discussion/reset", { method: "POST" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      const err = await response.json();
      setStatus(`Unable to reset: ${err.detail || response.statusText}`);
      return;
    }
    followLiveEdge = true;
    await fetchSnapshot();
  } catch (error) {
    setStatus("Failed to reset discussion.");
  }
}

async function startNewDiscussionFromMenu() {
  closeMobileDrawer();
  await resetDiscussion();
}

document.addEventListener("mobile-drawer-action", async (event) => {
  const action = event?.detail?.action;
  if (action === "new-discussion") {
    await startNewDiscussionFromMenu();
  }
});

promptEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    sendPrompt();
  }
});

promptEl.addEventListener("input", autoGrowPrompt);
conversationEl.addEventListener("scroll", () => {
  followLiveEdge = atLiveEdge();
  updateScrollLatestVisibility();
});
window.addEventListener("resize", syncBottomInset);
window.addEventListener(
  "scroll",
  () => {
    followLiveEdge = atLiveEdge();
    updateScrollLatestVisibility();
  },
  { passive: true }
);
if (scrollLatestButtonEl) {
  scrollLatestButtonEl.addEventListener("click", () => {
    scrollConversationToBottom("smooth");
  });
}

async function startPolling() {
  autoGrowPrompt();
  syncBottomInset();
  await loadUserLabel();
  await fetchSnapshot();
  if (pollHandle) {
    clearInterval(pollHandle);
  }
  pollHandle = setInterval(fetchSnapshot, 1000);
}

startPolling();
