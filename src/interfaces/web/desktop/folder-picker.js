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

function createFolderPickerDialog({ title, folders, defaultFolderId }) {
  const overlay = document.createElement("div");
  overlay.className = "folder-picker-overlay";

  const dialog = document.createElement("div");
  dialog.className = "folder-picker";
  overlay.appendChild(dialog);

  const heading = document.createElement("h3");
  heading.className = "folder-picker-title";
  heading.innerText = title || "Choose parent folder";
  dialog.appendChild(heading);

  const path = document.createElement("div");
  path.className = "folder-picker-path";
  dialog.appendChild(path);

  const list = document.createElement("div");
  list.className = "folder-picker-list";
  dialog.appendChild(list);

  const actions = document.createElement("div");
  actions.className = "folder-picker-actions";
  dialog.appendChild(actions);

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "small-button";
  cancelBtn.innerText = "Cancel";
  actions.appendChild(cancelBtn);

  const useBtn = document.createElement("button");
  useBtn.type = "button";
  useBtn.innerText = "Use Selected Folder";
  actions.appendChild(useBtn);

  const childrenByParent = buildFolderIndex(folders || []);
  const folderById = new Map((folders || []).map((folder) => [String(folder.id), folder]));
  let browsingFolderId = defaultFolderId == null ? null : Number(defaultFolderId);

  function parentOf(folderId) {
    if (folderId == null) {
      return null;
    }
    const folder = folderById.get(String(folderId));
    return folder ? folder.parent_id : null;
  }

  function currentPath(folderId) {
    const chain = [];
    let cursor = folderId;
    const seen = new Set();
    while (cursor != null && !seen.has(String(cursor))) {
      seen.add(String(cursor));
      const folder = folderById.get(String(cursor));
      if (!folder) {
        break;
      }
      chain.push(folder.name);
      cursor = folder.parent_id;
    }
    chain.reverse();
    return ["Root", ...chain];
  }

  function renderPath() {
    path.innerText = currentPath(browsingFolderId).join(" / ");
  }

  function makeRowButton(label, onClick, isActive = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "folder-picker-row";
    if (isActive) {
      button.classList.add("is-active");
    }
    button.innerText = label;
    button.onclick = onClick;
    return button;
  }

  function renderList() {
    list.innerHTML = "";

    if (browsingFolderId != null) {
      list.appendChild(
        makeRowButton("← Up One Level", () => {
          browsingFolderId = parentOf(browsingFolderId);
          renderPath();
          renderList();
        })
      );
    }

    const children = childrenByParent.get(browsingFolderId == null ? "root" : String(browsingFolderId)) || [];
    children.forEach((folder) => {
      list.appendChild(
        makeRowButton(`Open ${folder.name} ›`, () => {
          browsingFolderId = Number(folder.id);
          renderPath();
          renderList();
        }, false)
      );
    });
  }

  renderPath();
  renderList();

  return {
    overlay,
    cancelBtn,
    useBtn,
    getSelectedFolderId: () => browsingFolderId,
  };
}

window.pickFolderParent = function pickFolderParent({ title, folders, defaultFolderId }) {
  return new Promise((resolve) => {
    const dialog = createFolderPickerDialog({ title, folders, defaultFolderId });
    document.body.appendChild(dialog.overlay);

    function close(result) {
      dialog.overlay.remove();
      resolve(result);
    }

    dialog.cancelBtn.onclick = () => close({ confirmed: false, folderId: null });
    dialog.useBtn.onclick = () => close({ confirmed: true, folderId: dialog.getSelectedFolderId() });
    dialog.overlay.addEventListener("click", (event) => {
      if (event.target === dialog.overlay) {
        close({ confirmed: false, folderId: null });
      }
    });
  });
};
