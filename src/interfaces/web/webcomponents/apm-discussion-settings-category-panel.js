class ApmDiscussionSettingsCategoryPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        .field {
          display: grid;
          gap: 0.45rem;
        }

        label {
          font-weight: 600;
          color: var(--text-secondary);
        }

        textarea {
          width: 100%;
          min-height: 130px;
          border: 1px solid var(--card-border);
          border-radius: 8px;
          background: var(--input-bg);
          color: var(--text-secondary);
          padding: 0.65rem 0.75rem;
          box-sizing: border-box;
          font: inherit;
          resize: vertical;
          line-height: 1.35;
        }

        .hint {
          color: var(--text-muted);
          font-size: 0.9rem;
          margin: 0;
        }
      </style>
      <div class="field">
        <label for="system-prompt">System Prompt</label>
        <textarea id="system-prompt" placeholder="Enter the default system prompt..."></textarea>
        <p class="hint">Default behavior guidance used when starting a discussion.</p>
      </div>
    `;
  }

  connectedCallback() {
    this._systemPromptEl().addEventListener("input", () => {
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  _systemPromptEl() {
    return this.shadowRoot.getElementById("system-prompt");
  }

  getValues() {
    return {
      system_prompt: this._systemPromptEl().value || "",
    };
  }

  setValues(values) {
    this._systemPromptEl().value = values.system_prompt || "";
  }
}

if (!customElements.get("apm-discussion-settings-category-panel")) {
  customElements.define("apm-discussion-settings-category-panel", ApmDiscussionSettingsCategoryPanel);
}
