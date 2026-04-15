(function initApmPanelRegistry(globalScope) {
  const panelDefs = [
    {
      id: "discussion.main",
      title: "Discussion",
      component_tag: "apm-discussion-page",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "read", other: "none" },
    },
    {
      id: "discussion.tree",
      title: "Discussion Tree",
      component_tag: "apm-discussion-tree-page",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "read", other: "none" },
    },
    {
      id: "discussion.participants",
      title: "Participants",
      component_tag: "apm-discussion-participants-panel",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "read", other: "read" },
    },
    {
      id: "discussion.settings",
      title: "Discussion Settings",
      component_tag: "apm-discussion-settings-panel",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "read", other: "none" },
    },
    {
      id: "settings.ai",
      title: "AI Settings",
      component_tag: "apm-ai-settings-panel",
      owner_user_id: 1,
      owner_group_id: 10,
      permissions: { owner: "write", group: "none", other: "none" },
    },
    {
      id: "settings.discussion",
      title: "Discussion Settings",
      component_tag: "apm-discussion-settings-category-panel",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "read", other: "none" },
    },
    {
      id: "settings.theme",
      title: "Theme Settings",
      component_tag: "apm-theme-settings-panel",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "write", other: "read" },
    },
    {
      id: "settings.about",
      title: "About",
      component_tag: "apm-about-panel",
      owner_user_id: 1,
      owner_group_id: 1,
      permissions: { owner: "write", group: "read", other: "read" },
    },
  ];

  const defaultDiscussionLayout = {
    type: "row",
    content: [
      {
        type: "panel",
        panelId: "discussion.tree",
        size: 24,
      },
      {
        type: "panel",
        panelId: "discussion.main",
        size: 51,
      },
      {
        type: "column",
        size: 25,
        content: [
          {
            type: "panel",
            panelId: "discussion.participants",
            size: 50,
          },
          {
            type: "panel",
            panelId: "discussion.settings",
            size: 50,
          },
        ],
      },
    ],
  };

  function listPanels() {
    return panelDefs.slice();
  }

  function getPanelById(panelId) {
    return panelDefs.find((panel) => panel.id === panelId) || null;
  }

  function registerPanel(panelDef) {
    if (!panelDef || typeof panelDef !== "object") {
      throw new Error("Invalid panel definition.");
    }
    if (!panelDef.id || !panelDef.component_tag) {
      throw new Error("Panel definition requires id and component_tag.");
    }
    if (getPanelById(panelDef.id)) {
      throw new Error(`Panel id already registered: ${panelDef.id}`);
    }
    panelDefs.push(panelDef);
    return panelDef;
  }

  function getDefaultDiscussionLayout() {
    return JSON.parse(JSON.stringify(defaultDiscussionLayout));
  }

  globalScope.ApmPanelRegistry = {
    listPanels,
    getPanelById,
    registerPanel,
    getDefaultDiscussionLayout,
  };
})(window);
