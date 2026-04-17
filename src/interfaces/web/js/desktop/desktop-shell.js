import { GoldenLayout } from "/vendor/golden-layout/esm/index.min.js";

const DEFAULT_USER_CONTEXT = {
  userId: null,
  groupIds: [],
};

function setDesktopStatus(text) {
  const statusEl = document.getElementById("desktop-shell-status");
  if (statusEl) {
    statusEl.innerText = text;
  }
}

async function loadCurrentUserContext() {
  try {
    const sessionResponse = await fetch("/api/auth/session");
    if (!sessionResponse.ok) {
      return { ...DEFAULT_USER_CONTEXT };
    }
    const session = await sessionResponse.json();
    if (!session || !session.authenticated) {
      return { ...DEFAULT_USER_CONTEXT };
    }

    let groupIds = [];
    try {
      const groupsResponse = await fetch("/api/groups");
      if (groupsResponse.ok) {
        const groupsPayload = await groupsResponse.json();
        const groups = Array.isArray(groupsPayload?.groups) ? groupsPayload.groups : [];
        groupIds = groups
          .map((group) => Number(group?.id))
          .filter((groupId) => Number.isInteger(groupId));
      }
    } catch (_error) {
      // Fallback to no group memberships when groups endpoint is unavailable.
    }

    return {
      userId: Number.isInteger(Number(session.user_id)) ? Number(session.user_id) : null,
      groupIds,
    };
  } catch (_error) {
    return { ...DEFAULT_USER_CONTEXT };
  }
}

function getPanelRuntimeState(registry, permissions, panelId, userContext) {
  const panelDef = registry.getPanelById(panelId);
  const accessMode = permissions.getEffectivePermission(panelDef, userContext);
  return {
    accessMode,
    canRead: accessMode === "read" || accessMode === "write",
    canWrite: accessMode === "write",
  };
}

function setupMenuPlaceholders() {
  ["file", "edit", "admin", "help"].forEach((menuName) => {
    const buttonEl = document.querySelector(`[data-desktop-menu="${menuName}"]`);
    if (!buttonEl) {
      return;
    }
    buttonEl.addEventListener("click", () => {
      const label = menuName[0].toUpperCase() + menuName.slice(1);
      setDesktopStatus(`${label} menu is a placeholder.`);
    });
  });
}

function filterLayoutByReadablePanels(node, canReadPanelById) {
  if (!node || typeof node !== "object") {
    return null;
  }
  if (node.type === "panel") {
    return canReadPanelById(node.panelId) ? { ...node } : null;
  }
  const content = Array.isArray(node.content)
    ? node.content.map((item) => filterLayoutByReadablePanels(item, canReadPanelById)).filter(Boolean)
    : [];
  if (content.length === 0) {
    return null;
  }
  return {
    ...node,
    content,
  };
}

async function initDesktopWorkspace() {
  const registry = window.ApmPanelRegistry;
  const permissions = window.ApmPanelPermissions;
  const layoutApi = window.ApmLayoutManager;
  const rootEl = document.getElementById("desktop-layout-root");
  const viewButtonEl = document.querySelector('[data-desktop-menu="view"]');

  if (!registry || !permissions || !layoutApi || !rootEl || !viewButtonEl) {
    setDesktopStatus("Desktop shell warning: panel foundation modules are unavailable.");
    return;
  }

  const userContext = await loadCurrentUserContext();
  const panels = registry.listPanels();
  const readable = panels.filter((panel) => permissions.canReadPanel(panel, userContext)).length;
  const writable = panels.filter((panel) => permissions.canWritePanel(panel, userContext)).length;

  const defaultLayout = typeof registry.getDefaultDiscussionLayout === "function"
    ? registry.getDefaultDiscussionLayout()
    : null;
  const filteredLayout = filterLayoutByReadablePanels(
    defaultLayout,
    (panelId) => permissions.canReadPanel(registry.getPanelById(panelId), userContext)
  );
  if (!filteredLayout) {
    setDesktopStatus("Desktop shell: no readable panels for the current user.");
    return;
  }

  const layoutManager = layoutApi.createLayoutManager({
    rootElement: rootEl,
    onStatus: setDesktopStatus,
    goldenLayoutCtor: GoldenLayout,
  });
  if (!layoutManager.init()) {
    return;
  }

  layoutManager.registerPanelHost(
    "apm-panel-host",
    (panelId) => registry.getPanelById(panelId),
    (panelId) => getPanelRuntimeState(registry, permissions, panelId, userContext)
  );
  layoutManager.loadLayout(filteredLayout);
  const canReadPanelById = (panelId) => permissions.canReadPanel(registry.getPanelById(panelId), userContext);

  function openPanelById(panelId) {
    const panelDef = registry.getPanelById(panelId);
    if (!panelDef) {
      setDesktopStatus(`Panel not found: ${panelId}`);
      return false;
    }
    if (!canReadPanelById(panelId)) {
      setDesktopStatus(`Access denied: ${panelDef.title}`);
      return false;
    }
    const runtimeState = getPanelRuntimeState(registry, permissions, panelId, userContext);
    return layoutManager.openPanel(panelId, panelDef.title, { componentState: runtimeState });
  }

  function closeViewMenu(menuEl) {
    menuEl.hidden = true;
    viewButtonEl.setAttribute("aria-expanded", "false");
  }

  function renderViewMenu() {
    const existing = document.getElementById("desktop-view-menu");
    if (existing) {
      existing.remove();
    }
    const menuEl = document.createElement("div");
    menuEl.id = "desktop-view-menu";
    menuEl.className = "desktop-view-menu";
    menuEl.setAttribute("role", "menu");
    menuEl.hidden = true;

    const readablePanels = panels.filter((panel) => canReadPanelById(panel.id));
    readablePanels.forEach((panel) => {
      const runtimeState = getPanelRuntimeState(registry, permissions, panel.id, userContext);
      const buttonEl = document.createElement("button");
      buttonEl.type = "button";
      buttonEl.className = "desktop-view-menu-item";
      buttonEl.setAttribute("role", "menuitem");
      buttonEl.innerText = panel.title;
      buttonEl.dataset.panelId = panel.id;
      buttonEl.dataset.accessMode = runtimeState.accessMode;
      buttonEl.addEventListener("click", () => {
        openPanelById(panel.id);
        closeViewMenu(menuEl);
      });
      menuEl.appendChild(buttonEl);
    });

    viewButtonEl.after(menuEl);
    viewButtonEl.setAttribute("aria-haspopup", "menu");
    viewButtonEl.setAttribute("aria-expanded", "false");
    viewButtonEl.addEventListener("click", (event) => {
      event.stopPropagation();
      menuEl.hidden = !menuEl.hidden;
      viewButtonEl.setAttribute("aria-expanded", String(!menuEl.hidden));
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !menuEl.hidden) {
        closeViewMenu(menuEl);
      }
    });
    document.addEventListener("click", (event) => {
      if (!menuEl.hidden && !menuEl.contains(event.target) && event.target !== viewButtonEl) {
        closeViewMenu(menuEl);
      }
    });
  }

  renderViewMenu();
  window.ApmDesktopShell = {
    openPanelById,
    currentUserContext: { ...userContext },
  };

  setDesktopStatus(`Discussion workspace loaded. Panels: ${panels.length} (${readable} read / ${writable} write).`);
}

setupMenuPlaceholders();
initDesktopWorkspace();
