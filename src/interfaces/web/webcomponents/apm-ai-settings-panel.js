class ApmAISettingsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        .field {
          display: grid;
          gap: 0.45rem;
          margin-bottom: 0.9rem;
        }

        .field:last-child {
          margin-bottom: 0;
        }

        label {
          font-weight: 600;
          color: var(--text-secondary);
        }

        input {
          width: 100%;
          border: 1px solid var(--card-border);
          border-radius: 8px;
          background: var(--input-bg);
          color: var(--text-secondary);
          padding: 0.65rem 0.75rem;
          box-sizing: border-box;
          font: inherit;
        }

        .hint {
          color: var(--text-muted);
          font-size: 0.9rem;
          margin: 0;
        }
      </style>
      <div class="field">
        <label for="model-url">Model URL</label>
        <input id="model-url" type="url" placeholder="http://localhost:5001" />
        <p class="hint">Base URL used to reach the configured text model backend.</p>
      </div>
      <div class="field">
        <label for="max-response-size">Max Response Size</label>
        <input id="max-response-size" type="number" min="1" step="1" placeholder="8192" />
        <p class="hint">Maximum token count allowed for model responses.</p>
      </div>
    `;
  }

  connectedCallback() {
    const notifyChange = () => {
      this.dispatchEvent(new Event("change", { bubbles: true }));
    };
    this._modelUrlEl().addEventListener("input", notifyChange);
    this._maxResponseSizeEl().addEventListener("input", notifyChange);
  }

  _modelUrlEl() {
    return this.shadowRoot.getElementById("model-url");
  }

  _maxResponseSizeEl() {
    return this.shadowRoot.getElementById("max-response-size");
  }

  getValues() {
    return {
      model_url: (this._modelUrlEl().value || "").trim(),
      max_response_size: Number(this._maxResponseSizeEl().value || 0),
    };
  }

  setValues(values) {
    this._modelUrlEl().value = values.model_url || "";
    this._maxResponseSizeEl().value = String(values.max_response_size || 8192);
  }
}

if (!customElements.get("apm-ai-settings-panel")) {
  customElements.define("apm-ai-settings-panel", ApmAISettingsPanel);
}
