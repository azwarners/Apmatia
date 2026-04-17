class ApmDiscussionSettingsPanel extends HTMLElement {
  constructor() {
    super();
    this._values = { system_prompt: "" };
    this._promptId = `apm-system-prompt-${Math.random().toString(36).slice(2, 10)}`;
    this._isSaving = false;
  }

  connectedCallback() {
    this.render();
    this.loadCurrentPrompt();
  }

  getValues() {
    const promptEl = this.querySelector(".apm-system-prompt");
    return {
      system_prompt: promptEl ? promptEl.value || "" : this._values.system_prompt || "",
    };
  }

  setValues(values) {
    this._values = {
      system_prompt: values?.system_prompt || "",
    };
    const promptEl = this.querySelector(".apm-system-prompt");
    if (promptEl) {
      promptEl.value = this._values.system_prompt;
    }
  }

  render() {
    this.innerHTML = `
      <section class="apm-panel apm-discussion-settings-panel" aria-label="Discussion settings">
        <header class="apm-panel-header">Discussion Settings</header>
        <div class="apm-panel-body">
          <label for="${this._promptId}" class="apm-panel-label">System Prompt</label>
          <textarea
            id="${this._promptId}"
            class="apm-system-prompt"
            rows="6"
            placeholder="Behavior guidance used when starting a discussion."
          ></textarea>
          <button type="button" class="apm-apply-settings-button">Apply</button>
          <div class="status apm-settings-status" aria-live="polite"></div>
        </div>
      </section>
    `;

    const promptEl = this.querySelector(".apm-system-prompt");
    const applyButtonEl = this.querySelector(".apm-apply-settings-button");
    promptEl.value = this._values.system_prompt;
    this.setStatus("Ready.");

    promptEl.addEventListener("input", () => {
      this._values.system_prompt = promptEl.value || "";
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });

    applyButtonEl.addEventListener("click", () => this.saveSystemPrompt());
  }

  setStatus(text) {
    const statusEl = this.querySelector(".apm-settings-status");
    if (statusEl) {
      statusEl.innerText = text;
    }
  }

  setApplyDisabled(disabled) {
    const applyButtonEl = this.querySelector(".apm-apply-settings-button");
    if (applyButtonEl) {
      applyButtonEl.disabled = Boolean(disabled);
    }
  }

  async loadCurrentPrompt() {
    try {
      const response = await fetch("/api/discussion/state");
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        this.setStatus("Unable to load system prompt.");
        return;
      }
      const snapshot = await response.json();
      this.setValues({
        system_prompt: snapshot.system_prompt || "",
      });
      this.setStatus("Ready.");
    } catch (error) {
      this.setStatus("Unable to load system prompt.");
    }
  }

  async saveSystemPrompt() {
    if (this._isSaving) {
      return;
    }
    const payload = this.getValues();
    this._isSaving = true;
    this.setApplyDisabled(true);
    this.setStatus("Saving...");
    try {
      const response = await fetch("/api/discussion/system_prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        this.setStatus(err.detail || "Unable to save system prompt.");
        return;
      }
      this.setStatus("System prompt saved.");
      this.dispatchEvent(
        new CustomEvent("apm-discussion-settings-apply", {
          bubbles: true,
          detail: payload,
        })
      );
    } catch (error) {
      this.setStatus("Unable to save system prompt.");
    } finally {
      this._isSaving = false;
      this.setApplyDisabled(false);
    }
  }
}

if (!customElements.get("apm-discussion-settings-panel")) {
  customElements.define("apm-discussion-settings-panel", ApmDiscussionSettingsPanel);
}
