const _BaseTreeListItem = window.TreeListItem || HTMLElement;

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

class DiscussionTreeListItem extends _BaseTreeListItem {
  constructor() {
    super();
    this.dataset.treeItem = "true";
  }
}

class DiscussionFolderListItem extends DiscussionTreeListItem {
  setData(folder) {
    this._folder = folder;
    this.render();
  }

  render() {
    const folder = this._folder;
    if (!folder) {
      this.innerHTML = "";
      return;
    }

    this.className = "tree-folder-row";
    this.innerHTML = "";

    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.className = "tree-folder-open";
    openBtn.setAttribute("aria-label", `Open folder ${folder.name}`);
    openBtn.addEventListener("click", () => {
      this.emit("tree-folder-open", { folder });
    });

    const name = document.createElement("span");
    name.className = "tree-folder-link-name";
    name.innerText = folder.name;
    openBtn.appendChild(name);

    const arrow = document.createElement("span");
    arrow.className = "tree-folder-link-arrow";
    arrow.innerText = "\u203A";
    openBtn.appendChild(arrow);
    this.appendChild(openBtn);

    const menuWrap = document.createElement("div");
    menuWrap.className = "tree-row-menu";

    const menuButton = document.createElement("button");
    menuButton.type = "button";
    menuButton.className = "tree-meatballs-button";
    menuButton.setAttribute("aria-label", "Folder actions");
    menuButton.innerText = "\u22ef";
    menuButton.addEventListener("click", (event) => {
      event.stopPropagation();
      this.requestMenuToggle();
    });
    menuWrap.appendChild(menuButton);

    const menu = document.createElement("div");
    menu.className = "tree-menu";
    menu.hidden = true;

    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.innerText = "Rename";
    renameBtn.addEventListener("click", () => {
      this.emit("tree-folder-rename", { folder });
    });
    menu.appendChild(renameBtn);

    const moveBtn = document.createElement("button");
    moveBtn.type = "button";
    moveBtn.innerText = "Move";
    moveBtn.addEventListener("click", () => {
      this.emit("tree-folder-move", { folder });
    });
    menu.appendChild(moveBtn);

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.innerText = "Delete";
    deleteBtn.addEventListener("click", () => {
      this.emit("tree-folder-delete", { folder });
    });
    menu.appendChild(deleteBtn);

    const shareBtn = document.createElement("button");
    shareBtn.type = "button";
    shareBtn.innerText = "Sharing: \uD83D\uDD12 Private";
    shareBtn.disabled = true;
    menu.appendChild(shareBtn);

    menuWrap.appendChild(menu);
    this.appendChild(menuWrap);

    this.setMenuElements(menu, menuButton);
  }
}

class DiscussionEntryListItem extends DiscussionTreeListItem {
  setData(discussion, depth = 0) {
    this._discussion = discussion;
    this._depth = Number(depth) || 0;
    this.render();
  }

  render() {
    const discussion = this._discussion;
    if (!discussion) {
      this.innerHTML = "";
      return;
    }

    this.className = "tree-discussion";
    this.style.paddingLeft = `${this._depth * 16}px`;
    this.innerHTML = "";

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

    this.appendChild(titleBlock);

    const menuWrap = document.createElement("div");
    menuWrap.className = "tree-row-menu";

    const menuButton = document.createElement("button");
    menuButton.type = "button";
    menuButton.className = "tree-meatballs-button";
    menuButton.setAttribute("aria-label", "Discussion actions");
    menuButton.innerText = "\u22ef";
    menuButton.addEventListener("click", (event) => {
      event.stopPropagation();
      this.requestMenuToggle();
    });
    menuWrap.appendChild(menuButton);

    const menu = document.createElement("div");
    menu.className = "tree-menu";
    menu.hidden = true;

    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.innerText = "Open";
    openBtn.addEventListener("click", () => {
      this.emit("tree-discussion-open", { discussion });
    });
    menu.appendChild(openBtn);

    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.innerText = "Rename";
    renameBtn.addEventListener("click", () => {
      this.emit("tree-discussion-rename", { discussion });
    });
    menu.appendChild(renameBtn);

    const groupBtn = document.createElement("button");
    groupBtn.type = "button";
    groupBtn.innerText = sharingLabel(discussion);
    groupBtn.addEventListener("click", () => {
      this.emit("tree-discussion-group", { discussion });
    });
    menu.appendChild(groupBtn);

    const folderBtn = document.createElement("button");
    folderBtn.type = "button";
    folderBtn.innerText = "Add to Folder";
    folderBtn.addEventListener("click", () => {
      this.emit("tree-discussion-folder", { discussion });
    });
    menu.appendChild(folderBtn);

    menuWrap.appendChild(menu);
    this.appendChild(menuWrap);

    this.setMenuElements(menu, menuButton);
  }
}

customElements.define("discussion-tree-list-item", DiscussionTreeListItem);
customElements.define("discussion-folder-list-item", DiscussionFolderListItem);
customElements.define("discussion-entry-list-item", DiscussionEntryListItem);
