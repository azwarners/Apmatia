const _BaseTreeList = window.TreeList || HTMLElement;

function _folderKey(folderId) {
  return folderId == null ? "root" : String(folderId);
}

class DiscussionTree extends _BaseTreeList {
  constructor() {
    super();
    this._state = { folders: [], discussions: [], currentFolderId: null };
    this._boundListClick = this._handleListClick.bind(this);
    this._boundToggleMenu = this._handleToggleMenu.bind(this);
  }

  connectedCallback() {
    if (super.connectedCallback) {
      super.connectedCallback();
    }
    this.addEventListener("click", this._boundListClick);
    this.addEventListener("tree-item-toggle-menu", this._boundToggleMenu);
  }

  disconnectedCallback() {
    this.removeEventListener("click", this._boundListClick);
    this.removeEventListener("tree-item-toggle-menu", this._boundToggleMenu);
    if (super.disconnectedCallback) {
      super.disconnectedCallback();
    }
  }

  _handleListClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      this.closeAllMenus();
      return;
    }
    if (!target.closest(".tree-row-menu")) {
      this.closeAllMenus();
    }
  }

  _handleToggleMenu(event) {
    const item = event?.detail?.item;
    if (!item || typeof item.isMenuOpen !== "function") {
      return;
    }
    if (item.isMenuOpen()) {
      item.closeMenu();
      return;
    }
    this.closeAllMenus(item);
    item.openMenu();
  }

  _discussionsMap() {
    const map = new Map();
    (this._state.discussions || []).forEach((discussion) => {
      const key = discussion.folder_id == null ? "root" : String(discussion.folder_id);
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key).push(discussion);
    });
    return map;
  }

  _childrenByParent() {
    const map = new Map();
    (this._state.folders || []).forEach((folder) => {
      const key = folder.parent_id == null ? "root" : String(folder.parent_id);
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key).push(folder);
    });
    return map;
  }

  setTreeData({ folders = [], discussions = [], currentFolderId = null }) {
    this._state = {
      folders,
      discussions,
      currentFolderId,
    };
    this.render();
  }

  render() {
    this.innerHTML = "";

    const currentFolderId = this._state.currentFolderId;
    const childrenByParent = this._childrenByParent();
    const discussionsByFolder = this._discussionsMap();

    const currentChildren = childrenByParent.get(_folderKey(currentFolderId)) || [];
    currentChildren.forEach((folder) => {
      const item = document.createElement("discussion-folder-list-item");
      item.setData(folder);
      this.appendChild(item);
    });

    const currentDiscussions = discussionsByFolder.get(_folderKey(currentFolderId)) || [];
    currentDiscussions.forEach((discussion) => {
      const item = document.createElement("discussion-entry-list-item");
      item.setData(discussion, 0);
      this.appendChild(item);
    });
  }
}

customElements.define("discussion-tree-list", DiscussionTree);
