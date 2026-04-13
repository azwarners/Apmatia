function sortFoldersByName(folders) {
  return [...folders].sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
}

function buildFolderIndex(folders) {
  const childrenByParent = new Map();
  folders.forEach((folder) => {
    const key = folder.parent_id == null ? "root" : String(folder.parent_id);
    if (!childrenByParent.has(key)) {
      childrenByParent.set(key, []);
    }
    childrenByParent.get(key).push(folder);
  });
  childrenByParent.forEach((list, key) => {
    childrenByParent.set(key, sortFoldersByName(list));
  });
  return childrenByParent;
}

class FolderPickerDialog extends HTMLElement {
  open({ title, folders, defaultFolderId }) {
    const config = {
      title: title || "Choose parent folder",
      folders: folders || [],
      defaultFolderId: defaultFolderId == null ? null : Number(defaultFolderId),
    };

    return new Promise((resolve) => {
      this._resolve = resolve;
      this._childrenByParent = buildFolderIndex(config.folders);
      this._folderById = new Map(config.folders.map((folder) => [String(folder.id), folder]));
      this._browsingFolderId = config.defaultFolderId;
      this._title = config.title;
      this.render();
    });
  }

  _close(result) {
    this.remove();
    if (typeof this._resolve === "function") {
      this._resolve(result);
      this._resolve = null;
    }
  }

  _parentOf(folderId) {
    if (folderId == null) {
      return null;
    }
    const folder = this._folderById.get(String(folderId));
    return folder ? folder.parent_id : null;
  }

  _currentPath(folderId) {
    const chain = [];
    let cursor = folderId;
    const seen = new Set();
    while (cursor != null && !seen.has(String(cursor))) {
      seen.add(String(cursor));
      const folder = this._folderById.get(String(cursor));
      if (!folder) {
        break;
      }
      chain.push(folder.name);
      cursor = folder.parent_id;
    }
    chain.reverse();
    return ["Root", ...chain];
  }

  _makeRowButton(label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "folder-picker-row";
    button.innerText = label;
    button.onclick = onClick;
    return button;
  }

  _renderList(listEl, pathEl) {
    listEl.innerHTML = "";
    pathEl.innerText = this._currentPath(this._browsingFolderId).join(" / ");

    if (this._browsingFolderId != null) {
      listEl.appendChild(
        this._makeRowButton("\u2190 Up One Level", () => {
          this._browsingFolderId = this._parentOf(this._browsingFolderId);
          this._renderList(listEl, pathEl);
        })
      );
    }

    const key = this._browsingFolderId == null ? "root" : String(this._browsingFolderId);
    const children = this._childrenByParent.get(key) || [];
    children.forEach((folder) => {
      listEl.appendChild(
        this._makeRowButton(`Open ${folder.name} \u203A`, () => {
          this._browsingFolderId = Number(folder.id);
          this._renderList(listEl, pathEl);
        })
      );
    });
  }

  render() {
    this.innerHTML = "";
    this.className = "folder-picker-overlay";

    const dialog = document.createElement("div");
    dialog.className = "folder-picker";

    const heading = document.createElement("h3");
    heading.className = "folder-picker-title";
    heading.innerText = this._title;
    dialog.appendChild(heading);

    const path = document.createElement("div");
    path.className = "folder-picker-path";
    dialog.appendChild(path);

    const list = document.createElement("div");
    list.className = "folder-picker-list";
    dialog.appendChild(list);

    const actions = document.createElement("div");
    actions.className = "folder-picker-actions";

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "small-button";
    cancelBtn.innerText = "Cancel";
    cancelBtn.onclick = () => this._close({ confirmed: false, folderId: null });
    actions.appendChild(cancelBtn);

    const useBtn = document.createElement("button");
    useBtn.type = "button";
    useBtn.innerText = "Use Selected Folder";
    useBtn.onclick = () => this._close({ confirmed: true, folderId: this._browsingFolderId });
    actions.appendChild(useBtn);

    dialog.appendChild(actions);
    this.appendChild(dialog);

    this.addEventListener("click", (event) => {
      if (event.target === this) {
        this._close({ confirmed: false, folderId: null });
      }
    });

    this._renderList(list, path);
  }
}

customElements.define("folder-picker-dialog", FolderPickerDialog);

window.pickFolderParent = function pickFolderParent(config) {
  const picker = document.createElement("folder-picker-dialog");
  document.body.appendChild(picker);
  return picker.open(config || {});
};
