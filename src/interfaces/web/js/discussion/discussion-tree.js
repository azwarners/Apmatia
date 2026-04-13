const treeEl = document.getElementById("discussion-tree");
const statusEl = document.getElementById("tree-status");
const folderNavEl = document.getElementById("folder-nav");
const createFolderButtonEl = document.getElementById("create-folder-button");

let treeState = { current_discussion_id: null, folders: [], discussions: [] };
const folderBrowser = new FolderBrowserState();

function setStatus(text) {
  statusEl.innerText = text;
}

function renderFolderNav() {
  if (!folderNavEl) {
    return;
  }

  const label = folderBrowser.getCurrentLabel();
  const isRoot = folderBrowser.getCurrentFolderId() == null;
  const parentLabel = folderBrowser.getParentLabel();
  if (typeof folderNavEl.setState === "function") {
    folderNavEl.setState({ isRoot, label, parentLabel });
  }
}

function renderTree() {
  renderFolderNav();
  if (!treeEl || typeof treeEl.setTreeData !== "function") {
    return;
  }
  treeEl.setTreeData({
    folders: treeState.folders || [],
    discussions: treeState.discussions || [],
    currentFolderId: folderBrowser.getCurrentFolderId(),
  });
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
  if (typeof window.pickFolderParent !== "function") {
    setStatus("Folder picker is unavailable.");
    return;
  }
  const selection = await window.pickFolderParent({
    title: `Move \"${discussion.title}\" to...`,
    folders: treeState.folders || [],
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
    setStatus(err.detail || "Unable to move discussion.");
    return;
  }
  await loadTree();
}

async function renameFolder(folder) {
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
    title: `Move \"${folder.name}\" to...`,
    folders: treeState.folders || [],
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

  await loadTree();
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

  if (typeof window.pickFolderParent !== "function") {
    setStatus("Folder picker is unavailable.");
    return;
  }

  const currentFolderId = folderBrowser.getCurrentFolderId();
  const selection = await window.pickFolderParent({
    title: `Choose parent folder for \"${cleanName}\"`,
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

if (createFolderButtonEl) {
  createFolderButtonEl.addEventListener("click", createFolder);
}

if (folderNavEl) {
  folderNavEl.addEventListener("navigate-up", () => {
    folderBrowser.goParent();
    renderTree();
  });
}

if (treeEl) {
  treeEl.addEventListener("tree-folder-open", (event) => {
    const folder = event?.detail?.folder;
    if (!folder) {
      return;
    }
    folderBrowser.enterFolder(folder.id);
    renderTree();
  });

  treeEl.addEventListener("tree-folder-rename", async (event) => {
    const folder = event?.detail?.folder;
    if (folder) {
      await renameFolder(folder);
    }
  });

  treeEl.addEventListener("tree-folder-move", async (event) => {
    const folder = event?.detail?.folder;
    if (folder) {
      await moveFolder(folder);
    }
  });

  treeEl.addEventListener("tree-folder-delete", async (event) => {
    const folder = event?.detail?.folder;
    if (folder) {
      await deleteFolder(folder);
    }
  });

  treeEl.addEventListener("tree-discussion-open", async (event) => {
    const discussion = event?.detail?.discussion;
    if (discussion) {
      await openDiscussion(discussion.discussion_id);
    }
  });

  treeEl.addEventListener("tree-discussion-rename", async (event) => {
    const discussion = event?.detail?.discussion;
    if (discussion) {
      await renameDiscussion(discussion);
    }
  });

  treeEl.addEventListener("tree-discussion-group", async (event) => {
    const discussion = event?.detail?.discussion;
    if (discussion) {
      await setDiscussionGroup(discussion);
    }
  });

  treeEl.addEventListener("tree-discussion-folder", async (event) => {
    const discussion = event?.detail?.discussion;
    if (discussion) {
      await setDiscussionFolder(discussion);
    }
  });
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
