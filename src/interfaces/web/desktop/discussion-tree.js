const treeEl = document.getElementById("discussion-tree");
const statusEl = document.getElementById("tree-status");
const folderNavEl = document.getElementById("folder-nav");
const createFolderButtonEl = document.getElementById("create-folder-button");

let treeState = { current_discussion_id: null, folders: [], discussions: [] };
let openMenuId = null;
const folderBrowser = new FolderBrowserState();

function setStatus(text) {
  statusEl.innerText = text;
}

function discussionsMap(discussions) {
  const map = new Map();
  discussions.forEach((discussion) => {
    const key = discussion.folder_id == null ? "root" : String(discussion.folder_id);
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key).push(discussion);
  });
  return map;
}

function folderKey(folderId) {
  return folderId == null ? "root" : String(folderId);
}

function sharingLabel(discussion) {
  if (discussion.visibility === "group" && discussion.group_id != null) {
    return `Sharing: Group ${discussion.group_id}`;
  }
  return "Sharing: \uD83D\uDD12 Private";
}

function formatCreatedAt(isoText) {
  if (!isoText) {
    return "Created: unknown";
  }
  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) {
    return "Created: unknown";
  }
  const formatted = new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
  return `Created: ${formatted}`;
}

function closeAllMenus() {
  openMenuId = null;
  treeEl.querySelectorAll(".tree-menu").forEach((menu) => {
    menu.hidden = true;
  });
}

function renderFolderNav() {
  if (!folderNavEl) {
    return;
  }

  const label = folderBrowser.getCurrentLabel();
  const isRoot = folderBrowser.getCurrentFolderId() == null;
  folderNavEl.innerHTML = "";

  const bar = document.createElement("div");
  bar.className = "folder-nav-bar";

  if (isRoot) {
    const rootLabel = document.createElement("span");
    rootLabel.className = "folder-nav-label";
    rootLabel.innerText = "Root";
    bar.appendChild(rootLabel);
  } else {
    const parentLabel = folderBrowser.getParentLabel();
    const backBtn = document.createElement("button");
    backBtn.type = "button";
    backBtn.className = "folder-nav-back";
    backBtn.innerText = `\u2190 ${parentLabel}`;
    backBtn.onclick = () => {
      folderBrowser.goParent();
      renderTree();
    };
    bar.appendChild(backBtn);

    const currentLabel = document.createElement("span");
    currentLabel.className = "folder-nav-label";
    currentLabel.innerText = label;
    bar.appendChild(currentLabel);
  }

  folderNavEl.appendChild(bar);
}

function toggleMenu(menuEl, itemId) {
  if (openMenuId === itemId) {
    closeAllMenus();
    return;
  }
  closeAllMenus();
  menuEl.hidden = false;
  openMenuId = itemId;
}

async function openDiscussion(discussionId) {
  const response = await fetch(`/api/discussions/${encodeURIComponent(discussionId)}/open`, {
    method: "POST",
  });
  if (response.status === 401) {
    window.location.href = "/login";
    return;
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    setStatus(err.detail || "Unable to open discussion.");
    return;
  }
  window.location.href = "/discussion";
}

async function renameDiscussion(discussion) {
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
    setStatus(err.detail || "Unable to rename discussion.");
    return;
  }
  await loadTree();
}

async function setDiscussionGroup(discussion) {
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
    setStatus(err.detail || "Unable to update discussion group.");
    return;
  }
  await loadTree();
}

async function setDiscussionFolder(discussion) {
  const payload = { folder_id: discussion.folder_id == null ? null : Number(discussion.folder_id) };
  const response = await fetch(`/api/discussions/${encodeURIComponent(discussion.discussion_id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    setStatus(err.detail || "Unable to move discussion.");
    return;
  }
  await loadTree();
}

function renderFolderPicker(menu, discussion) {
  const existing = menu.querySelector(".tree-folder-picker");
  if (existing) {
    existing.remove();
    return;
  }

  const picker = document.createElement("div");
  picker.className = "tree-folder-picker";

  const rootBtn = document.createElement("button");
  rootBtn.type = "button";
  rootBtn.className = "tree-folder-option";
  rootBtn.innerText = discussion.folder_id == null ? "In Root (Current)" : "Move to Root";
  rootBtn.disabled = discussion.folder_id == null;
  rootBtn.onclick = async () => {
    discussion.folder_id = null;
    await setDiscussionFolder(discussion);
    closeAllMenus();
  };
  picker.appendChild(rootBtn);

  treeState.folders.forEach((folder) => {
    const folderBtn = document.createElement("button");
    folderBtn.type = "button";
    folderBtn.className = "tree-folder-option";
    const isCurrent = Number(discussion.folder_id) === Number(folder.id);
    folderBtn.innerText = isCurrent ? `${folder.name} (Current)` : folder.name;
    folderBtn.disabled = isCurrent;
    folderBtn.onclick = async () => {
      discussion.folder_id = Number(folder.id);
      await setDiscussionFolder(discussion);
      closeAllMenus();
    };
    picker.appendChild(folderBtn);
  });

  menu.appendChild(picker);
}

function listDescendantFolderIds(folderId) {
  const byParent = new Map();
  (treeState.folders || []).forEach((folder) => {
    const key = folder.parent_id == null ? "root" : String(folder.parent_id);
    if (!byParent.has(key)) {
      byParent.set(key, []);
    }
    byParent.get(key).push(folder);
  });

  const descendants = new Set();
  const stack = [String(folderId)];
  while (stack.length > 0) {
    const current = stack.pop();
    const children = byParent.get(current) || [];
    children.forEach((child) => {
      const childId = String(child.id);
      if (!descendants.has(childId)) {
        descendants.add(childId);
        stack.push(childId);
      }
    });
  }
  return descendants;
}

async function renameFolder(folder) {
  const name = window.prompt("Rename folder", folder.name || "");
  if (name == null) {
    return;
  }
  const cleanName = name.trim();
  if (!cleanName) {
    setStatus("Folder name is required.");
    return;
  }
  const response = await fetch(`/api/discussions/folders/${encodeURIComponent(folder.id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: cleanName }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    setStatus(err.detail || "Unable to rename folder.");
    return;
  }
  await loadTree();
}

async function moveFolder(folder) {
  if (typeof window.pickFolderParent !== "function") {
    setStatus("Folder picker is unavailable.");
    return;
  }
  const selection = await window.pickFolderParent({
    title: `Move "${folder.name}" to...`,
    folders: treeState.folders || [],
    defaultFolderId: folder.parent_id,
  });
  if (!selection || !selection.confirmed) {
    return;
  }

  const selectedId = selection.folderId == null ? null : Number(selection.folderId);
  const descendantIds = listDescendantFolderIds(folder.id);
  if (selectedId === Number(folder.id) || (selectedId != null && descendantIds.has(String(selectedId)))) {
    setStatus("Folder cannot be moved into itself or its descendants.");
    return;
  }

  const response = await fetch(`/api/discussions/folders/${encodeURIComponent(folder.id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: selectedId }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    setStatus(err.detail || "Unable to move folder.");
    return;
  }
  await loadTree();
}

async function deleteFolder(folder) {
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
    setStatus(err.detail || "Unable to delete folder.");
    return;
  }

  closeAllMenus();
  await loadTree();
}

function makeDiscussionRow(discussion, depth) {
  const row = document.createElement("div");
  row.className = "tree-discussion";
  row.style.paddingLeft = `${depth * 16}px`;

  const titleBlock = document.createElement("div");
  titleBlock.className = "tree-discussion-title";

  const title = document.createElement("span");
  title.className = "tree-discussion-name";
  title.innerText = discussion.title;
  titleBlock.appendChild(title);

  const meta = document.createElement("span");
  meta.className = "meta";
  meta.innerText = formatCreatedAt(discussion.created_at);
  titleBlock.appendChild(meta);

  row.appendChild(titleBlock);

  const menuWrap = document.createElement("div");
  menuWrap.className = "tree-row-menu";

  const menuButton = document.createElement("button");
  menuButton.type = "button";
  menuButton.className = "tree-meatballs-button";
  menuButton.setAttribute("aria-label", "Discussion actions");
  menuButton.innerText = "\u22ef";
  menuWrap.appendChild(menuButton);

  const menu = document.createElement("div");
  menu.className = "tree-menu";
  menu.hidden = true;

  const openBtn = document.createElement("button");
  openBtn.type = "button";
  openBtn.innerText = "Open";
  openBtn.onclick = () => openDiscussion(discussion.discussion_id);
  menu.appendChild(openBtn);

  const renameBtn = document.createElement("button");
  renameBtn.type = "button";
  renameBtn.innerText = "Rename";
  renameBtn.onclick = () => renameDiscussion(discussion);
  menu.appendChild(renameBtn);

  const groupBtn = document.createElement("button");
  groupBtn.type = "button";
  groupBtn.innerText = sharingLabel(discussion);
  groupBtn.onclick = () => setDiscussionGroup(discussion);
  menu.appendChild(groupBtn);

  const folderBtn = document.createElement("button");
  folderBtn.type = "button";
  folderBtn.innerText = "Add to Folder";
  folderBtn.onclick = (event) => {
    event.stopPropagation();
    renderFolderPicker(menu, discussion);
  };
  menu.appendChild(folderBtn);

  menuButton.onclick = (event) => {
    event.stopPropagation();
    toggleMenu(menu, `discussion:${discussion.discussion_id}`);
  };

  menuWrap.appendChild(menu);
  row.appendChild(menuWrap);

  return row;
}

function makeFolderRow(folder) {
  const row = document.createElement("div");
  row.className = "tree-folder-row";

  const openBtn = document.createElement("button");
  openBtn.type = "button";
  openBtn.className = "tree-folder-open";
  openBtn.setAttribute("aria-label", `Open folder ${folder.name}`);
  openBtn.onclick = () => {
    folderBrowser.enterFolder(folder.id);
    renderTree();
  };

  const name = document.createElement("span");
  name.className = "tree-folder-link-name";
  name.innerText = folder.name;
  openBtn.appendChild(name);

  const arrow = document.createElement("span");
  arrow.className = "tree-folder-link-arrow";
  arrow.innerText = "\u203A";
  openBtn.appendChild(arrow);
  row.appendChild(openBtn);

  const menuWrap = document.createElement("div");
  menuWrap.className = "tree-row-menu";

  const menuButton = document.createElement("button");
  menuButton.type = "button";
  menuButton.className = "tree-meatballs-button";
  menuButton.setAttribute("aria-label", "Folder actions");
  menuButton.innerText = "\u22ef";
  menuWrap.appendChild(menuButton);

  const menu = document.createElement("div");
  menu.className = "tree-menu";
  menu.hidden = true;

  const renameBtn = document.createElement("button");
  renameBtn.type = "button";
  renameBtn.innerText = "Rename";
  renameBtn.onclick = () => renameFolder(folder);
  menu.appendChild(renameBtn);

  const moveBtn = document.createElement("button");
  moveBtn.type = "button";
  moveBtn.innerText = "Move";
  moveBtn.onclick = () => moveFolder(folder);
  menu.appendChild(moveBtn);

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.innerText = "Delete";
  deleteBtn.onclick = async () => {
    await deleteFolder(folder);
  };
  menu.appendChild(deleteBtn);

  const shareBtn = document.createElement("button");
  shareBtn.type = "button";
  shareBtn.innerText = "Sharing: \uD83D\uDD12 Private";
  shareBtn.disabled = true;
  menu.appendChild(shareBtn);

  menuButton.onclick = (event) => {
    event.stopPropagation();
    toggleMenu(menu, `folder:${folder.id}`);
  };

  menuWrap.appendChild(menu);
  row.appendChild(menuWrap);

  return row;
}

function renderTree() {
  treeEl.innerHTML = "";
  closeAllMenus();
  renderFolderNav();

  const folderDiscussions = discussionsMap(treeState.discussions);
  const currentFolderId = folderBrowser.getCurrentFolderId();

  const currentChildren = folderBrowser.getChildren(currentFolderId);
  currentChildren.forEach((folder) => {
    treeEl.appendChild(makeFolderRow(folder));
  });

  const currentDiscussions = folderDiscussions.get(folderKey(currentFolderId)) || [];
  currentDiscussions.forEach((discussion) => {
    treeEl.appendChild(makeDiscussionRow(discussion, 0));
  });
}

async function loadTree() {
  try {
    const response = await fetch("/api/discussions/tree");
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      setStatus("Unable to load discussions.");
      return;
    }
    treeState = await response.json();
    folderBrowser.setFolders(treeState.folders || []);
    renderTree();
    setStatus("Ready.");
  } catch (error) {
    setStatus("Unable to load discussions.");
  }
}

async function createFolder() {
  const name = window.prompt("New folder name", "");
  if (name == null) {
    return;
  }
  const cleanName = name.trim();
  if (!cleanName) {
    setStatus("Folder name is required.");
    return;
  }

  if (typeof window.pickFolderParent !== "function") {
    setStatus("Folder picker is unavailable.");
    return;
  }

  const currentFolderId = folderBrowser.getCurrentFolderId();
  const selection = await window.pickFolderParent({
    title: `Choose parent folder for "${cleanName}"`,
    folders: treeState.folders || [],
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
    setStatus(err.detail || "Unable to create folder.");
    return;
  }
  await loadTree();
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    closeAllMenus();
    return;
  }
  if (!target.closest(".tree-row-menu")) {
    closeAllMenus();
  }
});

if (createFolderButtonEl) {
  createFolderButtonEl.addEventListener("click", createFolder);
}

document.addEventListener("mobile-drawer-action", (event) => {
  const action = event?.detail?.action;
  if (action === "create-folder") {
    createFolder();
    return;
  }
  if (action === "trash-soon") {
    setStatus("Trash view is not implemented yet (placeholder).");
  }
});

loadTree();
