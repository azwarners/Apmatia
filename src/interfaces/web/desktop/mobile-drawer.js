function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

class MobileDrawer extends HTMLElement {
  connectedCallback() {
    this.render();
    this.bindActions();
  }

  parseItems() {
    const raw = this.getAttribute("items");
    if (!raw) {
      return [];
    }
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  renderItem(item) {
    const label = escapeHtml(item.label || "");
    if (item.type === "button") {
      const attrs = [];
      if (item.id) {
        attrs.push(`id="${escapeHtml(item.id)}"`);
      }
      if (item.className) {
        attrs.push(`class="${escapeHtml(item.className)}"`);
      }
      if (item.action) {
        attrs.push(`data-mobile-menu-action="${escapeHtml(item.action)}"`);
      }
      if (item.closeOnClick !== false) {
        attrs.push("data-mobile-menu-close");
      }
      return `<li><button type="button" ${attrs.join(" ")}>${label}</button></li>`;
    }

    const href = escapeHtml(item.href || "#");
    return `<li><a href="${href}" data-mobile-menu-close>${label}</a></li>`;
  }

  render() {
    const items = this.parseItems();
    const listHtml = items.map((item) => this.renderItem(item)).join("");
    this.innerHTML = `
      <div class="mobile-drawer-overlay" data-mobile-menu-close></div>
      <aside class="mobile-drawer">
        <ul class="mobile-drawer-links">${listHtml}</ul>
      </aside>
    `;
  }

  bindActions() {
    this.querySelectorAll("[data-mobile-menu-action]").forEach((el) => {
      el.addEventListener("click", () => {
        const action = el.getAttribute("data-mobile-menu-action");
        if (!action) {
          return;
        }
        document.dispatchEvent(
          new CustomEvent("mobile-drawer-action", {
            bubbles: true,
            detail: { action },
          })
        );
      });
    });
  }
}

customElements.define("mobile-drawer-menu", MobileDrawer);
