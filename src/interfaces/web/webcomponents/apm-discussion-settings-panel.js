class ApmDiscussionSettingsPanel extends HTMLElement {
  constructor() {
    super();
    this._values = { system_prompt: "" };
    this._promptId = `apm-system-prompt-${Math.random().toString(36).slice(2, 10)}`;
  }

  connectedCallback() {
    this.render();
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
        </div>
      </section>
    `;

    const promptEl = this.querySelector(".apm-system-prompt");
    const applyButtonEl = this.querySelector(".apm-apply-settings-button");
    promptEl.value = this._values.system_prompt;

    promptEl.addEventListener("input", () => {
      this._values.system_prompt = promptEl.value || "";
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });

    applyButtonEl.addEventListener("click", () => {
      this.dispatchEvent(
        new CustomEvent("apm-discussion-settings-apply", {
          bubbles: true,
          detail: this.getValues(),
        })
      );
    });
  }
}

if (!customElements.get("apm-discussion-settings-panel")) {
  customElements.define("apm-discussion-settings-panel", ApmDiscussionSettingsPanel);
}
