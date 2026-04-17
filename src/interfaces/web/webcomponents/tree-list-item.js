class TreeListItem extends HTMLElement {
  constructor() {
    super();
    this._menuEl = null;
    this._menuButtonEl = null;
  }

  connectedCallback() {
    if (!this.dataset.treeItem) {
      this.dataset.treeItem = "true";
    }
  }

  setMenuElements(menuEl, menuButtonEl) {
    this._menuEl = menuEl || null;
    this._menuButtonEl = menuButtonEl || null;
  }

  isMenuOpen() {
    return Boolean(this._menuEl) && !this._menuEl.hidden;
  }

  openMenu() {
    if (this._menuEl) {
      this._menuEl.hidden = false;
    }
  }

  closeMenu() {
    if (this._menuEl) {
      this._menuEl.hidden = true;
    }
  }

  requestMenuToggle() {
    this.dispatchEvent(
      new CustomEvent("tree-item-toggle-menu", {
        bubbles: true,
        detail: { item: this },
      })
    );
  }

  emit(eventName, detail = {}) {
    this.dispatchEvent(new CustomEvent(eventName, { bubbles: true, detail }));
  }
}

window.TreeListItem = TreeListItem;
customElements.define("tree-list-item", TreeListItem);
