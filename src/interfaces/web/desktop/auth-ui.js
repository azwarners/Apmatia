async function logoutApmatia() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (error) {
    // best effort logout; continue to login either way
  }
  window.location.href = "/login";
}

function closeAllUserMenus() {
  document.querySelectorAll(".user-menu.is-open").forEach((menuEl) => {
    menuEl.classList.remove("is-open");
  });
}

function buildUserMenu() {
  const menuEl = document.createElement("div");
  menuEl.className = "user-menu";
  menuEl.innerHTML = `
    <a href="/settings#profile">User Profile</a>
    <a href="/settings#users">User Management</a>
    <button type="button" class="logout-action">Logout</button>
  `;
  menuEl.querySelector(".logout-action").addEventListener("click", logoutApmatia);
  return menuEl;
}

function initUserMenus() {
  const toggles = Array.from(document.querySelectorAll(".mobile-icon-button.logout-action"));
  toggles.forEach((toggleEl) => {
    toggleEl.classList.remove("logout-action");
    toggleEl.classList.add("user-menu-toggle");
    const parentEl = toggleEl.parentElement;
    if (!parentEl) {
      return;
    }
    const menuEl = buildUserMenu();
    parentEl.appendChild(menuEl);
    toggleEl.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = menuEl.classList.contains("is-open");
      closeAllUserMenus();
      if (!isOpen) {
        menuEl.classList.add("is-open");
      }
    });
  });

  document.addEventListener("click", () => {
    closeAllUserMenus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllUserMenus();
    }
  });
}

initUserMenus();

document.querySelectorAll(".logout-action").forEach((el) => {
  el.addEventListener("click", logoutApmatia);
});
