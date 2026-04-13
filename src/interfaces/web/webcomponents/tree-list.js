class TreeList extends HTMLElement {
  constructor() {
    super();
    this._onDocumentClick = this._onDocumentClick.bind(this);
  }

  connectedCallback() {
    document.addEventListener("click", this._onDocumentClick);
  }

  disconnectedCallback() {
    document.removeEventListener("click", this._onDocumentClick);
  }

  _onDocumentClick(event) {
    if (!(event.target instanceof Node)) {
      this.closeAllMenus();
      return;
    }
    if (!this.contains(event.target)) {
      this.closeAllMenus();
    }
  }

  closeAllMenus(exceptItem = null) {
    this.querySelectorAll('[data-tree-item="true"]').forEach((itemEl) => {
      if (itemEl !== exceptItem && typeof itemEl.closeMenu === "function") {
        itemEl.closeMenu();
      }
    });
  }
}

window.TreeList = TreeList;
customElements.define("tree-list", TreeList);
