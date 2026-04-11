class FolderBrowserState {
  constructor() {
    this.currentFolderId = null;
    this.folderById = new Map();
    this.childrenByParent = new Map();
  }

  _parentKey(parentId) {
    return parentId == null ? "root" : String(parentId);
  }

  _hasFolder(folderId) {
    return folderId != null && this.folderById.has(String(folderId));
  }

  setFolders(folders) {
    this.folderById = new Map();
    this.childrenByParent = new Map();

    folders.forEach((folder) => {
      this.folderById.set(String(folder.id), folder);
      const key = this._parentKey(folder.parent_id);
      if (!this.childrenByParent.has(key)) {
        this.childrenByParent.set(key, []);
      }
      this.childrenByParent.get(key).push(folder);
    });

    if (!this._hasFolder(this.currentFolderId)) {
      this.currentFolderId = null;
    }
  }

  getCurrentFolderId() {
    return this.currentFolderId;
  }

  getCurrentFolder() {
    if (!this._hasFolder(this.currentFolderId)) {
      return null;
    }
    return this.folderById.get(String(this.currentFolderId)) || null;
  }

  getCurrentLabel() {
    const current = this.getCurrentFolder();
    return current ? current.name : "Root";
  }

  getParentFolderId() {
    const current = this.getCurrentFolder();
    return current ? current.parent_id : null;
  }

  getParentLabel() {
    const parentId = this.getParentFolderId();
    if (parentId == null) {
      return "Root";
    }
    const parent = this.folderById.get(String(parentId));
    return parent ? parent.name : "Root";
  }

  goRoot() {
    this.currentFolderId = null;
  }

  goParent() {
    this.currentFolderId = this.getParentFolderId();
  }

  enterFolder(folderId) {
    if (this._hasFolder(folderId)) {
      this.currentFolderId = Number(folderId);
    }
  }

  getChildren(folderId) {
    const key = this._parentKey(folderId);
    return this.childrenByParent.get(key) || [];
  }
}

window.FolderBrowserState = FolderBrowserState;
