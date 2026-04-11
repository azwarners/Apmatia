const treeEl = document.getElementById("discussion-tree");
const statusEl = document.getElementById("tree-status");
const createFolderButtonEl = document.getElementById("create-folder-button");
const drawerCreateFolderButtonEl = document.getElementById("drawer-create-folder-button");

let treeState = { current_discussion_id: null, folders: [], discussions: [] };
let openMenuDiscussionId = null;

function setStatus(text) {
  statusEl.innerText = text;
}

function childrenMap(folders) {
  const map = new Map();
  folders.forEach((folder) => {
    const key = folder.parent_id == null ? "root" : String(folder.parent_id);
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key).push(folder);
  });
  return map;
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

function buildFolderOptionsText() {
  const lines = ["Leave empty for root folder."];
  treeState.folders.forEach((folder) => {
    lines.push(`${folder.id}: ${folder.name}`);
  });
  return lines.join("\n");
}

function badgeText(discussion) {
  const badges = [];
  if (discussion.visibility === "group") {
    badges.push(`group:${discussion.group_id}`);
  } else {
    badges.push("private");
  }
  if (discussion.discussion_id === treeState.current_discussion_id) {
    badges.push("current");
  }
  return badges.join(", ");
}

function closeAllMenus() {
  openMenuDiscussionId = null;
  treeEl.querySelectorAll(".tree-menu").forEach((menu) => {
    menu.hidden = true;
  });
}

function toggleMenu(menuEl, discussionId) {
  if (openMenuDiscussionId === discussionId) {
    closeAllMenus();
    return;
  }
  closeAllMenus();
  menuEl.hidden = false;
  openMenuDiscussionId = discussionId;
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
  const raw = window.prompt(
    `Set folder ID for "${discussion.title}".\n${buildFolderOptionsText()}`,
    discussion.folder_id == null ? "" : String(discussion.folder_id)
  );
  if (raw == null) {
    return;
  }
  const value = raw.trim();
  const payload = { folder_id: value === "" ? null : Number(value) };
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
  meta.innerText = `(${badgeText(discussion)})`;
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
  groupBtn.innerText = "Set Group";
  groupBtn.onclick = () => setDiscussionGroup(discussion);
  menu.appendChild(groupBtn);

  const folderBtn = document.createElement("button");
  folderBtn.type = "button";
  folderBtn.innerText = "Add to Folder";
  folderBtn.onclick = () => setDiscussionFolder(discussion);
  menu.appendChild(folderBtn);

  menuButton.onclick = (event) => {
    event.stopPropagation();
    toggleMenu(menu, discussion.discussion_id);
  };

  menuWrap.appendChild(menu);
  row.appendChild(menuWrap);

  return row;
}

function renderFolder(folder, depth, folderChildren, folderDiscussions) {
  const details = document.createElement("details");
  details.className = "tree-folder";
  details.style.marginLeft = `${depth * 16}px`;
  details.open = true;

  const summary = document.createElement("summary");
  summary.className = "tree-folder-summary";
  summary.innerText = folder.name;
  details.appendChild(summary);

  const content = document.createElement("div");
  content.className = "tree-folder-content";

  const discussions = folderDiscussions.get(String(folder.id)) || [];
  discussions.forEach((discussion) => {
    content.appendChild(makeDiscussionRow(discussion, 1));
  });

  const children = folderChildren.get(String(folder.id)) || [];
  children.forEach((child) => {
    content.appendChild(renderFolder(child, 1, folderChildren, folderDiscussions));
  });

  details.appendChild(content);
  return details;
}

function renderTree() {
  treeEl.innerHTML = "";
  closeAllMenus();

  const folderChildren = childrenMap(treeState.folders);
  const folderDiscussions = discussionsMap(treeState.discussions);

  const rootDiscussions = folderDiscussions.get("root") || [];
  rootDiscussions.forEach((discussion) => {
    treeEl.appendChild(makeDiscussionRow(discussion, 0));
  });

  const roots = folderChildren.get("root") || [];
  roots.forEach((folder) => {
    treeEl.appendChild(renderFolder(folder, 0, folderChildren, folderDiscussions));
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

  const rawParent = window.prompt(`Optional parent folder ID\n${buildFolderOptionsText()}`, "");
  if (rawParent === null) {
    return;
  }
  const parentValue = (rawParent || "").trim();
  const parentId = parentValue === "" ? null : Number(parentValue);

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
if (drawerCreateFolderButtonEl) {
  drawerCreateFolderButtonEl.addEventListener("click", createFolder);
}

loadTree();
