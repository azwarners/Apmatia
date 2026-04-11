class ThemeSettings extends HTMLElement {
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

        select,
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
        <label for="theme-mode">Theme Mode</label>
        <select id="theme-mode">
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </select>
        <p class="hint">Choose dark (default) or light mode.</p>
      </div>
      <div class="field">
        <label for="font-family">Font Family</label>
        <select id="font-family">
          <option value="system-ui">System UI</option>
          <option value="serif">Serif</option>
          <option value="monospace">Monospace</option>
        </select>
        <p class="hint">Set the default UI font family.</p>
      </div>
      <div class="field">
        <label for="font-size">Font Size</label>
        <input id="font-size" type="number" min="12" max="24" step="1" />
        <p class="hint">Base font size in pixels (12-24).</p>
      </div>
      <div class="field">
        <label for="title-bar-height">Mobile Title Bar Height</label>
        <input id="title-bar-height" type="number" min="40" max="96" step="1" />
        <p class="hint">Height in pixels for the fixed mobile title bar (40-96).</p>
      </div>
      <div class="field">
        <label for="title-bar-font-size">Mobile Title Font Size</label>
        <input id="title-bar-font-size" type="number" min="12" max="40" step="1" />
        <p class="hint">Font size in pixels for the mobile title text (12-40).</p>
      </div>
    `;
  }

  connectedCallback() {
    const notifyChange = () => {
      this.dispatchEvent(new Event("change", { bubbles: true }));
    };
    this._themeEl().addEventListener("change", notifyChange);
    this._fontFamilyEl().addEventListener("change", notifyChange);
    this._fontSizeEl().addEventListener("input", notifyChange);
    this._titleBarHeightEl().addEventListener("input", notifyChange);
    this._titleBarFontSizeEl().addEventListener("input", notifyChange);
  }

  _themeEl() {
    return this.shadowRoot.getElementById("theme-mode");
  }

  _fontFamilyEl() {
    return this.shadowRoot.getElementById("font-family");
  }

  _fontSizeEl() {
    return this.shadowRoot.getElementById("font-size");
  }

  _titleBarHeightEl() {
    return this.shadowRoot.getElementById("title-bar-height");
  }

  _titleBarFontSizeEl() {
    return this.shadowRoot.getElementById("title-bar-font-size");
  }

  getValues() {
    return {
      theme: this._themeEl().value || "dark",
      font_family: this._fontFamilyEl().value || "system-ui",
      font_size: Number(this._fontSizeEl().value || 16),
      title_bar_height: Number(this._titleBarHeightEl().value || 56),
      title_bar_font_size: Number(this._titleBarFontSizeEl().value || 20),
    };
  }

  setValues(values) {
    this._themeEl().value = values.theme || "dark";
    this._fontFamilyEl().value = values.font_family || "system-ui";
    this._fontSizeEl().value = String(values.font_size || 16);
    this._titleBarHeightEl().value = String(values.title_bar_height || 56);
    this._titleBarFontSizeEl().value = String(values.title_bar_font_size || 20);
  }
}

customElements.define("theme-settings", ThemeSettings);
