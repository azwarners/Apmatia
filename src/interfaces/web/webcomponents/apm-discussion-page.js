class ApmDiscussionPage extends HTMLElement {
  constructor() {
    super();
    this._state = {
      pollHandle: null,
      userLabel: "User",
      followLiveEdge: true,
    };
    this._els = {};
    this._handlers = {};
  }

  connectedCallback() {
    this.render();
    this.bindEvents();
    this.startPolling();
  }

  disconnectedCallback() {
    this.unbindEvents();
    if (this._state.pollHandle) {
      clearInterval(this._state.pollHandle);
      this._state.pollHandle = null;
    }
  }

  render() {
    this.innerHTML = `
      <div class="card apm-discussion-shell">
        <div class="header">
          <h1>Discussion</h1>
        </div>

        <div class="discussion-actions">
          <button type="button" class="apm-reset-button">New Discussion</button>
        </div>
        <div class="apm-discussion-conversation" aria-live="polite"></div>
        <button class="apm-scroll-latest-button" type="button" aria-label="Jump to latest messages">↓ Latest</button>
        <div class="discussion-bottom apm-discussion-bottom">
          <div class="status apm-discussion-status">Connecting...</div>
          <div class="composer">
            <button class="apm-send-button" type="button">Send Prompt</button>
            <textarea
              class="apm-prompt"
              rows="3"
              placeholder="Enter prompt (Markdown supported). Press Ctrl+Enter or Cmd+Enter to send."
            ></textarea>
          </div>
        </div>
      </div>
    `;

    this._els = {
      conversation: this.querySelector(".apm-discussion-conversation"),
      status: this.querySelector(".apm-discussion-status"),
      sendButton: this.querySelector(".apm-send-button"),
      resetButton: this.querySelector(".apm-reset-button"),
      prompt: this.querySelector(".apm-prompt"),
      scrollLatestButton: this.querySelector(".apm-scroll-latest-button"),
      discussionBottom: this.querySelector(".apm-discussion-bottom"),
    };
  }

  bindEvents() {
    const { prompt, resetButton, conversation, scrollLatestButton } = this._els;

    this._handlers.keydown = (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        this.sendPrompt();
      }
    };
    this._handlers.input = () => this.autoGrowPrompt();
    this._handlers.resetClick = () => this.resetDiscussion();
    this._handlers.conversationScroll = () => {
      this._state.followLiveEdge = this.atLiveEdge();
      this.updateScrollLatestVisibility();
    };
    this._handlers.resize = () => this.syncBottomInset();
    this._handlers.windowScroll = () => {
      this._state.followLiveEdge = this.atLiveEdge();
      this.updateScrollLatestVisibility();
    };
    this._handlers.scrollLatestClick = () => {
      this.scrollConversationToBottom("smooth");
    };

    prompt.addEventListener("keydown", this._handlers.keydown);
    prompt.addEventListener("input", this._handlers.input);
    resetButton.addEventListener("click", this._handlers.resetClick);
    conversation.addEventListener("scroll", this._handlers.conversationScroll);
    window.addEventListener("resize", this._handlers.resize);
    window.addEventListener("scroll", this._handlers.windowScroll, { passive: true });
    scrollLatestButton.addEventListener("click", this._handlers.scrollLatestClick);
  }

  unbindEvents() {
    const { prompt, resetButton, conversation, scrollLatestButton } = this._els;
    if (prompt) {
      prompt.removeEventListener("keydown", this._handlers.keydown);
      prompt.removeEventListener("input", this._handlers.input);
    }
    if (resetButton) {
      resetButton.removeEventListener("click", this._handlers.resetClick);
    }
    if (conversation) {
      conversation.removeEventListener("scroll", this._handlers.conversationScroll);
    }
    if (scrollLatestButton) {
      scrollLatestButton.removeEventListener("click", this._handlers.scrollLatestClick);
    }
    window.removeEventListener("resize", this._handlers.resize);
    window.removeEventListener("scroll", this._handlers.windowScroll);
  }

  setStatus(text) {
    this._els.status.innerText = text;
  }

  autoGrowPrompt() {
    const promptEl = this._els.prompt;
    promptEl.style.height = "auto";
    promptEl.style.height = `${promptEl.scrollHeight}px`;
    this.syncBottomInset();
  }

  isNearBottom() {
    const el = this._els.conversation;
    return el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
  }

  pageIsNearBottom() {
    const pageBottom = window.scrollY + window.innerHeight;
    return pageBottom >= document.documentElement.scrollHeight - 24;
  }

  updateScrollLatestVisibility() {
    const buttonEl = this._els.scrollLatestButton;
    const conversationEl = this._els.conversation;
    const conversationCanScroll = conversationEl.scrollHeight > conversationEl.clientHeight + 24;
    const pageCanScroll = document.documentElement.scrollHeight > window.innerHeight + 24;
    const shouldShow = (conversationCanScroll || pageCanScroll) && (!this.isNearBottom() || !this.pageIsNearBottom());
    buttonEl.classList.toggle("is-visible", shouldShow);
  }

  syncBottomInset() {
    const inset = Math.ceil(this._els.discussionBottom.getBoundingClientRect().height) + 16;
    this.style.setProperty("--discussion-bottom-height", `${inset}px`);
    this.updateScrollLatestVisibility();
  }

  atLiveEdge() {
    return this.isNearBottom() && this.pageIsNearBottom();
  }

  scrollConversationToBottom(behavior = "auto") {
    this._state.followLiveEdge = true;
    const conversationEl = this._els.conversation;
    conversationEl.scrollTo({ top: conversationEl.scrollHeight, behavior });
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior });
    this.updateScrollLatestVisibility();
  }

  toDisplayName(username) {
    const clean = String(username || "").trim();
    if (!clean) {
      return "User";
    }
    const firstToken = clean.split(/[\s._-]+/)[0] || clean;
    return firstToken.charAt(0).toUpperCase() + firstToken.slice(1);
  }

  async loadUserLabel() {
    try {
      const response = await fetch("/api/auth/session");
      if (!response.ok) {
        return;
      }
      const session = await response.json();
      this._state.userLabel = this.toDisplayName(session.username);
    } catch (error) {
      // Keep fallback label when session lookup fails.
    }
  }

  renderConversation(messages) {
    const conversationEl = this._els.conversation;
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
      label.textContent = role === "User" ? `${this._state.userLabel}:` : "Assistant:";

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

  renderSnapshot(snapshot) {
    this.renderConversation(snapshot.messages || []);

    if (this._state.followLiveEdge) {
      this.scrollConversationToBottom();
    } else {
      this.updateScrollLatestVisibility();
    }

    if (snapshot.is_streaming) {
      this.setStatus("Streaming response...");
      this._els.sendButton.disabled = true;
      this._els.resetButton.disabled = true;
    } else {
      this.setStatus(snapshot.last_error ? `Error: ${snapshot.last_error}` : "Idle");
      this._els.sendButton.disabled = false;
      this._els.resetButton.disabled = false;
    }
  }

  async fetchSnapshot() {
    try {
      const response = await fetch("/api/discussion/state");
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const snapshot = await response.json();
      this.renderSnapshot(snapshot);
    } catch (error) {
      this.setStatus("Connection lost. Retrying...");
    }
  }

  async sendPrompt() {
    const prompt = (this._els.prompt.value || "").trim();
    if (!prompt) {
      this.setStatus("Please enter a prompt.");
      return;
    }

    try {
      this._state.followLiveEdge = true;
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
        this.setStatus(`Unable to start: ${err.detail || response.statusText}`);
        return;
      }
      this._els.prompt.value = "";
      this.autoGrowPrompt();
      await this.fetchSnapshot();
    } catch (error) {
      this.setStatus("Failed to send prompt.");
    }
  }

  async resetDiscussion() {
    try {
      const response = await fetch("/api/discussion/reset", { method: "POST" });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        const err = await response.json();
        this.setStatus(`Unable to reset: ${err.detail || response.statusText}`);
        return;
      }
      this._state.followLiveEdge = true;
      await this.fetchSnapshot();
    } catch (error) {
      this.setStatus("Failed to reset discussion.");
    }
  }

  async startPolling() {
    this.autoGrowPrompt();
    this.syncBottomInset();
    await this.loadUserLabel();
    await this.fetchSnapshot();
    if (this._state.pollHandle) {
      clearInterval(this._state.pollHandle);
    }
    this._state.pollHandle = setInterval(() => this.fetchSnapshot(), 1000);
  }
}

if (!customElements.get("apm-discussion-page")) {
  customElements.define("apm-discussion-page", ApmDiscussionPage);
}
