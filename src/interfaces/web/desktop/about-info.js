class AboutInfo extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        .field {
          display: grid;
          gap: 0.45rem;
        }

        .label {
          font-weight: 600;
          color: var(--text-secondary);
        }

        .value {
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
        <div class="label">Version</div>
        <div id="version" class="value">Loading...</div>
        <p class="hint">Use this value for troubleshooting deployment/runtime mismatches.</p>
      </div>
    `;
  }

  setVersion(version) {
    const versionEl = this.shadowRoot.getElementById("version");
    versionEl.innerText = version || "unknown";
  }
}

customElements.define("about-info", AboutInfo);
