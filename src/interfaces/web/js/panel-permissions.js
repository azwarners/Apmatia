(function initApmPanelPermissions(globalScope) {
  const PERMISSION_NONE = "none";
  const PERMISSION_READ = "read";
  const PERMISSION_WRITE = "write";

  function normalizePermission(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (raw === PERMISSION_WRITE) {
      return PERMISSION_WRITE;
    }
    if (raw === PERMISSION_READ) {
      return PERMISSION_READ;
    }
    return PERMISSION_NONE;
  }

  function includesGroup(groupIds, ownerGroupId) {
    if (ownerGroupId == null) {
      return false;
    }
    const ids = Array.isArray(groupIds) ? groupIds : [];
    return ids.some((id) => Number(id) === Number(ownerGroupId));
  }

  function resolveAccessClass(panelDef, userContext) {
    if (!panelDef || typeof panelDef !== "object") {
      return "other";
    }

    const userId = Number(userContext?.userId);
    const ownerUserId = Number(panelDef.owner_user_id);

    if (Number.isFinite(userId) && Number.isFinite(ownerUserId) && userId === ownerUserId) {
      return "owner";
    }

    if (includesGroup(userContext?.groupIds, panelDef.owner_group_id)) {
      return "group";
    }

    return "other";
  }

  function getEffectivePermission(panelDef, userContext) {
    const accessClass = resolveAccessClass(panelDef, userContext);
    const permissions = panelDef?.permissions || {};
    return normalizePermission(permissions[accessClass]);
  }

  function canReadPanel(panelDef, userContext) {
    const permission = getEffectivePermission(panelDef, userContext);
    return permission === PERMISSION_READ || permission === PERMISSION_WRITE;
  }

  function canWritePanel(panelDef, userContext) {
    const permission = getEffectivePermission(panelDef, userContext);
    return permission === PERMISSION_WRITE;
  }

  globalScope.ApmPanelPermissions = {
    PERMISSION_NONE,
    PERMISSION_READ,
    PERMISSION_WRITE,
    normalizePermission,
    resolveAccessClass,
    getEffectivePermission,
    canReadPanel,
    canWritePanel,
  };
})(window);
