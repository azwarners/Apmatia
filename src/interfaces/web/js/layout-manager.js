(function initApmLayoutManager(globalScope) {
  function resolveRootElement(rootOrSelector) {
    if (!rootOrSelector) {
      return null;
    }
    if (rootOrSelector instanceof HTMLElement) {
      return rootOrSelector;
    }
    if (typeof rootOrSelector === "string") {
      return document.querySelector(rootOrSelector);
    }
    return null;
  }

  function createLayoutManager(config) {
    const rootEl = resolveRootElement(config?.rootElement || "#desktop-layout-root");
    const statusCallback = typeof config?.onStatus === "function" ? config.onStatus : () => {};
    const ctor = config?.goldenLayoutCtor || globalScope.GoldenLayout || null;

    const state = {
      rootEl,
      ctor,
      layout: null,
      hostPanelType: "apm-panel-host",
      resolvePanelFn: null,
      resolvePanelRuntimeStateFn: null,
    };

    function status(message) {
      statusCallback(String(message || ""));
    }

    function init() {
      if (!state.rootEl) {
        status("Layout manager: missing root element.");
        return false;
      }

      if (!state.ctor) {
        status("Layout manager ready: Golden Layout constructor unavailable.");
        return false;
      }

      if (state.layout) {
        return true;
      }

      try {
        state.layout = new state.ctor(state.rootEl);
        status("Layout manager initialized.");
        return true;
      } catch (errorA) {
        try {
          state.layout = new state.ctor({}, state.rootEl);
          status("Layout manager initialized.");
          return true;
        } catch (errorB) {
          status("Layout manager failed to initialize.");
          return false;
        }
      }
    }

    function registerPanelHost(hostPanelType, resolvePanelFn, resolvePanelRuntimeStateFn) {
      state.hostPanelType = hostPanelType || "apm-panel-host";
      state.resolvePanelFn = typeof resolvePanelFn === "function" ? resolvePanelFn : null;
      state.resolvePanelRuntimeStateFn = typeof resolvePanelRuntimeStateFn === "function"
        ? resolvePanelRuntimeStateFn
        : null;
      if (!state.layout || typeof state.layout.registerComponentFactoryFunction !== "function") {
        return false;
      }
      state.layout.registerComponentFactoryFunction(state.hostPanelType, (container, componentState) => {
        const panelId = componentState?.panelId;
        const panelDef = state.resolvePanelFn ? state.resolvePanelFn(panelId) : null;
        const accessMode = String(componentState?.accessMode || "none");

        const hostEl = document.createElement("div");
        hostEl.className = "apm-desktop-panel-host";
        hostEl.dataset.panelId = panelId || "";
        hostEl.dataset.accessMode = accessMode;

        if (panelDef && panelDef.component_tag) {
          const panelEl = document.createElement(panelDef.component_tag);
          panelEl.classList.add("apm-desktop-panel");
          panelEl.dataset.panelId = panelId || "";
          panelEl.dataset.accessMode = accessMode;
          panelEl.setAttribute("data-panel-id", panelId || "");
          panelEl.setAttribute("data-access-mode", accessMode);
          hostEl.appendChild(panelEl);
        } else {
          hostEl.innerText = panelId ? `Panel not found: ${panelId}` : "Panel not found";
        }

        const mountEl = container?.element || (typeof container?.getElement === "function" ? container.getElement() : null);
        if (mountEl) {
          mountEl.innerHTML = "";
          mountEl.appendChild(hostEl);
        }

        return {
          rootHtmlElement: hostEl,
          panelId,
          accessMode,
        };
      });
      return true;
    }

    function resolveComponentState(panelId, explicitState) {
      const baseState = explicitState && typeof explicitState === "object" ? explicitState : {};
      const extraState = state.resolvePanelRuntimeStateFn ? state.resolvePanelRuntimeStateFn(panelId) : {};
      return {
        panelId,
        ...baseState,
        ...extraState,
      };
    }

    function toGoldenSize(value) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric) || numeric <= 0) {
        return undefined;
      }
      return `${numeric}%`;
    }

    function toGoldenNode(node) {
      if (!node || typeof node !== "object") {
        return null;
      }
      if (node.type === "panel") {
        const result = {
          type: "component",
          title: node.title || node.panelId || "Panel",
          componentType: state.hostPanelType,
          componentState: resolveComponentState(node.panelId),
        };
        const size = toGoldenSize(node.size);
        if (size) {
          result.size = size;
        }
        return result;
      }
      const containerType = node.type === "column" ? "column" : "row";
      const children = Array.isArray(node.content) ? node.content.map(toGoldenNode).filter(Boolean) : [];
      if (children.length === 0) {
        return null;
      }
      const result = {
        type: containerType,
        content: children,
      };
      const size = toGoldenSize(node.size);
      if (size) {
        result.size = size;
      }
      return result;
    }

    function loadLayout(layoutConfig) {
      if (!state.layout && !init()) {
        return false;
      }
      if (!layoutConfig || typeof layoutConfig !== "object") {
        status("Layout manager: no layout config provided.");
        return false;
      }
      if (typeof state.layout.loadLayout === "function") {
        const rootNode = layoutConfig.root
          ? layoutConfig.root
          : toGoldenNode(layoutConfig);
        if (!rootNode) {
          status("Layout manager: layout has no renderable panels.");
          return false;
        }
        try {
          state.layout.loadLayout({
            root: rootNode,
          });
        } catch (error) {
          const detail = error && error.message ? error.message : "Unknown error";
          status(`Layout manager failed to load layout: ${detail}`);
          return false;
        }
        status("Layout loaded.");
        return true;
      }
      status("Layout manager: runtime does not support loadLayout.");
      return false;
    }

    function openPanel(panelId, title, options = {}) {
      if (!state.layout && !init()) {
        return false;
      }
      const panelDef = state.resolvePanelFn ? state.resolvePanelFn(panelId) : null;
      if (!panelDef) {
        status(`Layout manager: unknown panel ${panelId}.`);
        return false;
      }
      const componentState = resolveComponentState(panelId, options.componentState);
      if (componentState.canRead === false || componentState.accessMode === "none") {
        status(`Layout manager: access denied for panel ${panelId}.`);
        return false;
      }

      if (typeof state.layout.addComponent === "function") {
        state.layout.addComponent(
          state.hostPanelType,
          componentState,
          title || panelDef.title || panelId
        );
        status(`Opened panel: ${title || panelDef.title || panelId}.`);
        return true;
      }

      status("Layout manager: runtime does not support opening panels.");
      return false;
    }

    return {
      init,
      registerPanelHost,
      loadLayout,
      openPanel,
      getRootElement: () => state.rootEl,
      getLayoutInstance: () => state.layout,
    };
  }

  globalScope.ApmLayoutManager = {
    createLayoutManager,
  };
})(window);
