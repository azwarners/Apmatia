const discussionIdEl = document.getElementById("discussion-id");
const conversationEl = document.getElementById("conversation");
const statusEl = document.getElementById("status");
const sendButtonEl = document.getElementById("send-button");
const resetButtonEl = document.getElementById("reset-button");
const promptEl = document.getElementById("prompt");

let pollHandle = null;

function setStatus(text) {
  statusEl.innerText = text;
}

function renderSnapshot(snapshot) {
  const nearBottom =
    conversationEl.scrollTop + conversationEl.clientHeight >= conversationEl.scrollHeight - 24;

  discussionIdEl.innerText = snapshot.discussion_id;
  conversationEl.innerText = snapshot.content || "";

  if (nearBottom) {
    conversationEl.scrollTop = conversationEl.scrollHeight;
  }

  if (snapshot.is_streaming) {
    setStatus("Streaming response...");
    sendButtonEl.disabled = true;
    resetButtonEl.disabled = true;
  } else {
    setStatus(snapshot.last_error ? `Error: ${snapshot.last_error}` : "Idle");
    sendButtonEl.disabled = false;
    resetButtonEl.disabled = false;
  }
}

async function fetchSnapshot() {
  try {
    const response = await fetch("/api/discussion/state");
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
    const response = await fetch("/api/discussion/prompt", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    });
    if (!response.ok) {
      const err = await response.json();
      setStatus(`Unable to start: ${err.detail || response.statusText}`);
      return;
    }
    promptEl.value = "";
    await fetchSnapshot();
  } catch (error) {
    setStatus("Failed to send prompt.");
  }
}

async function resetDiscussion() {
  try {
    const response = await fetch("/api/discussion/reset", { method: "POST" });
    if (!response.ok) {
      const err = await response.json();
      setStatus(`Unable to reset: ${err.detail || response.statusText}`);
      return;
    }
    await fetchSnapshot();
  } catch (error) {
    setStatus("Failed to reset discussion.");
  }
}

promptEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendPrompt();
  }
});

async function startPolling() {
  await fetchSnapshot();
  if (pollHandle) {
    clearInterval(pollHandle);
  }
  pollHandle = setInterval(fetchSnapshot, 1000);
}

startPolling();
