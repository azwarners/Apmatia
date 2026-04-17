class ApmDiscussionTreePage extends HTMLElement {
  constructor() {
    super();
    this._els = {};
    this._state = { treeState: { current_discussion_id: null, folders: [], discussions: [] } };
    this._folderBrowser = new FolderBrowserState();
    this._pollHandle = null;
    this._boundHandlers = {};
  }

  connectedCallback() {
    this.render();
    this.bindEvents();
    this.loadTree();
    this.startPolling();
  }

  disconnectedCallback() {
    this.unbindEvents();
    if (this._pollHandle) {
      clearInterval(this._pollHandle);
      this._pollHandle = null;
    }
  }

  render() {
    this.innerHTML = `
      <div class="card apm-discussion-tree-shell">
        <div class="header">
          <h1>Discussion Tree</h1>
        </div>

        <div class="discussion-actions">
          <button type="button" class="apm-create-folder-button">Create Folder</button>
          <button type="button" class="secondary-action apm-trash-soon-button">Trash (Soon)</button>
        </div>
        <folder-browser-nav class="folder-nav apm-folder-nav"></folder-browser-nav>
        <discussion-tree-list class="tree-list apm-discussion-tree-list"></discussion-tree-list>
        <div class="status apm-discussion-tree-status">Loading discussions...</div>
      </div>
    `;

    this._els = {
      tree: this.querySelector(".apm-discussion-tree-list"),
      status: this.querySelector(".apm-discussion-tree-status"),
      folderNav: this.querySelector(".apm-folder-nav"),
      createFolderButton: this.querySelector(".apm-create-folder-button"),
      trashSoonButton: this.querySelector(".apm-trash-soon-button"),
    };
  }

  bindEvents() {
    const { createFolderButton, trashSoonButton, folderNav, tree } = this._els;

    this._boundHandlers.onCreateFolder = () => this.createFolder();
    this._boundHandlers.onTrashSoon = () => {
      this.setStatus("Trash view is not implemented yet (placeholder).");
    };
    this._boundHandlers.onNavigateUp = () => {
      this._folderBrowser.goParent();
      this.renderTree();
    };
    this._boundHandlers.onFolderOpen = (event) => {
      const folder = event?.detail?.folder;
      if (!folder) {
        return;
      }
      this._folderBrowser.enterFolder(folder.id);
      this.renderTree();
    };
    this._boundHandlers.onFolderRename = async (event) => {
      const folder = event?.detail?.folder;
      if (folder) {
        await this.renameFolder(folder);
      }
    };
    this._boundHandlers.onFolderMove = async (event) => {
      const folder = event?.detail?.folder;
      if (folder) {
        await this.moveFolder(folder);
      }
    };
    this._boundHandlers.onFolderDelete = async (event) => {
      const folder = event?.detail?.folder;
      if (folder) {
        await this.deleteFolder(folder);
      }
    };
    this._boundHandlers.onDiscussionOpen = async (event) => {
      const discussion = event?.detail?.discussion;
      if (discussion) {
        await this.openDiscussion(discussion.discussion_id);
      }
    };
    this._boundHandlers.onDiscussionRename = async (event) => {
      const discussion = event?.detail?.discussion;
      if (discussion) {
        await this.renameDiscussion(discussion);
      }
    };
    this._boundHandlers.onDiscussionGroup = async (event) => {
      const discussion = event?.detail?.discussion;
      if (discussion) {
        await this.setDiscussionGroup(discussion);
      }
    };
    this._boundHandlers.onDiscussionFolder = async (event) => {
      const discussion = event?.detail?.discussion;
      if (discussion) {
        await this.setDiscussionFolder(discussion);
      }
    };

    createFolderButton.addEventListener("click", this._boundHandlers.onCreateFolder);
    trashSoonButton.addEventListener("click", this._boundHandlers.onTrashSoon);
    folderNav.addEventListener("navigate-up", this._boundHandlers.onNavigateUp);

    tree.addEventListener("tree-folder-open", this._boundHandlers.onFolderOpen);
    tree.addEventListener("tree-folder-rename", this._boundHandlers.onFolderRename);
    tree.addEventListener("tree-folder-move", this._boundHandlers.onFolderMove);
    tree.addEventListener("tree-folder-delete", this._boundHandlers.onFolderDelete);
    tree.addEventListener("tree-discussion-open", this._boundHandlers.onDiscussionOpen);
    tree.addEventListener("tree-discussion-rename", this._boundHandlers.onDiscussionRename);
    tree.addEventListener("tree-discussion-group", this._boundHandlers.onDiscussionGroup);
    tree.addEventListener("tree-discussion-folder", this._boundHandlers.onDiscussionFolder);
  }

  unbindEvents() {
    const { createFolderButton, trashSoonButton, folderNav, tree } = this._els;
    if (createFolderButton) {
      createFolderButton.removeEventListener("click", this._boundHandlers.onCreateFolder);
    }
    if (trashSoonButton) {
      trashSoonButton.removeEventListener("click", this._boundHandlers.onTrashSoon);
    }
    if (folderNav) {
      folderNav.removeEventListener("navigate-up", this._boundHandlers.onNavigateUp);
    }
    if (!tree) {
      return;
    }
    tree.removeEventListener("tree-folder-open", this._boundHandlers.onFolderOpen);
    tree.removeEventListener("tree-folder-rename", this._boundHandlers.onFolderRename);
    tree.removeEventListener("tree-folder-move", this._boundHandlers.onFolderMove);
    tree.removeEventListener("tree-folder-delete", this._boundHandlers.onFolderDelete);
    tree.removeEventListener("tree-discussion-open", this._boundHandlers.onDiscussionOpen);
    tree.removeEventListener("tree-discussion-rename", this._boundHandlers.onDiscussionRename);
    tree.removeEventListener("tree-discussion-group", this._boundHandlers.onDiscussionGroup);
    tree.removeEventListener("tree-discussion-folder", this._boundHandlers.onDiscussionFolder);
  }

  setStatus(text) {
    this._els.status.innerText = text;
  }

  renderFolderNav() {
    const label = this._folderBrowser.getCurrentLabel();
    const isRoot = this._folderBrowser.getCurrentFolderId() == null;
    const parentLabel = this._folderBrowser.getParentLabel();
    if (typeof this._els.folderNav.setState === "function") {
      this._els.folderNav.setState({ isRoot, label, parentLabel });
    }
  }

  renderTree() {
    this.renderFolderNav();
    if (typeof this._els.tree.setTreeData !== "function") {
      return;
    }
    this._els.tree.setTreeData({
      folders: this._state.treeState.folders || [],
      discussions: this._state.treeState.discussions || [],
      currentFolderId: this._folderBrowser.getCurrentFolderId(),
    });
  }

  async openDiscussion(discussionId) {
    const response = await fetch(`/api/discussions/${encodeURIComponent(discussionId)}/open`, {
      method: "POST",
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to open discussion.");
      return;
    }
    window.location.href = "/discussion";
  }

  async renameDiscussion(discussion) {
    const title = window.prompt("Rename discussion", discussion.title || "");
    if (title == null) {
      return;
    }
    const response = await fetch(`/api/discussions/${encodeURIComponent(discussion.discussion_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to rename discussion.");
      return;
    }
    await this.loadTree();
  }

  async setDiscussionGroup(discussion) {
    const raw = window.prompt(
      "Set group ID for sharing. Leave empty to make private.",
      discussion.group_id == null ? "" : String(discussion.group_id)
    );
    if (raw == null) {
      return;
    }
    const value = raw.trim();
    const payload = { group_id: value === "" ? null : Number(value) };
    const response = await fetch(`/api/discussions/${encodeURIComponent(discussion.discussion_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to update discussion group.");
      return;
    }
    await this.loadTree();
  }

  async setDiscussionFolder(discussion) {
    if (typeof window.pickFolderParent !== "function") {
      this.setStatus("Folder picker is unavailable.");
      return;
    }
    const selection = await window.pickFolderParent({
      title: `Move \"${discussion.title}\" to...`,
      folders: this._state.treeState.folders || [],
      defaultFolderId: discussion.folder_id,
    });
    if (!selection || !selection.confirmed) {
      return;
    }

    const selectedId = selection.folderId == null ? null : Number(selection.folderId);
    const payload = { folder_id: selectedId };
    const response = await fetch(`/api/discussions/${encodeURIComponent(discussion.discussion_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to move discussion.");
      return;
    }
    await this.loadTree();
  }

  async renameFolder(folder) {
    const name = window.prompt("Rename folder", folder.name || "");
    if (name == null) {
      return;
    }
    const response = await fetch(`/api/discussions/folders/${encodeURIComponent(folder.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to rename folder.");
      return;
    }
    await this.loadTree();
  }

  async moveFolder(folder) {
    if (typeof window.pickFolderParent !== "function") {
      this.setStatus("Folder picker is unavailable.");
      return;
    }
    const selection = await window.pickFolderParent({
      title: `Move \"${folder.name}\" to...`,
      folders: this._state.treeState.folders || [],
      defaultFolderId: folder.parent_id,
    });
    if (!selection || !selection.confirmed) {
      return;
    }

    const selectedId = selection.folderId == null ? null : Number(selection.folderId);

    const response = await fetch(`/api/discussions/folders/${encodeURIComponent(folder.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parent_id: selectedId }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to move folder.");
      return;
    }
    await this.loadTree();
  }

  async deleteFolder(folder) {
    const runDelete = async (force) => {
      const url = force
        ? `/api/discussions/folders/${encodeURIComponent(folder.id)}?force=true`
        : `/api/discussions/folders/${encodeURIComponent(folder.id)}`;
      return fetch(url, { method: "DELETE" });
    };

    let response = await runDelete(false);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }

    if (response.status === 409) {
      const err = await response.json().catch(() => ({}));
      const shouldForce = window.confirm(
        `${err.detail || "Folder is not empty."}\n\nMove this folder and all contents to Trash?`
      );
      if (!shouldForce) {
        return;
      }
      response = await runDelete(true);
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to delete folder.");
      return;
    }

    await this.loadTree();
  }

  async loadTree() {
    try {
      const response = await fetch("/api/discussions/tree");
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        this.setStatus(err.detail || `Unable to load discussions (${response.status}).`);
        return;
      }
      this._state.treeState = await response.json();
      this._folderBrowser.setFolders(this._state.treeState.folders || []);
      this.renderTree();
      this.setStatus("Ready.");
    } catch (error) {
      this.setStatus("Unable to load discussions.");
    }
  }

  async createFolder() {
    const name = window.prompt("New folder name", "");
    if (name == null) {
      return;
    }
    const cleanName = name.trim();
    if (!cleanName) {
      this.setStatus("Folder name cannot be empty.");
      return;
    }

    if (typeof window.pickFolderParent !== "function") {
      this.setStatus("Folder picker is unavailable.");
      return;
    }

    const currentFolderId = this._folderBrowser.getCurrentFolderId();
    const selection = await window.pickFolderParent({
      title: `Choose parent folder for \"${cleanName}\"`,
      folders: this._state.treeState.folders || [],
      defaultFolderId: currentFolderId,
    });
    if (!selection || !selection.confirmed) {
      return;
    }
    const parentId = selection.folderId == null ? null : Number(selection.folderId);

    const response = await fetch("/api/discussions/folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: cleanName, parent_id: parentId }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      this.setStatus(err.detail || "Unable to create folder.");
      return;
    }
    await this.loadTree();
  }

  startPolling() {
    if (this._pollHandle) {
      clearInterval(this._pollHandle);
    }
    this._pollHandle = setInterval(() => {
      this.loadTree();
    }, 3000);
  }
}

if (!customElements.get("apm-discussion-tree-page")) {
  customElements.define("apm-discussion-tree-page", ApmDiscussionTreePage);
}
