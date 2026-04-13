function openMobileMenu() {
  document.body.classList.add("mobile-menu-open");
}

function closeMobileMenu() {
  document.body.classList.remove("mobile-menu-open");
}

document.querySelectorAll("[data-mobile-menu-toggle]").forEach((el) => {
  el.addEventListener("click", (event) => {
    event.preventDefault();
    openMobileMenu();
  });
});

document.querySelectorAll("[data-mobile-menu-close]").forEach((el) => {
  el.addEventListener("click", (event) => {
    if (!(el instanceof HTMLAnchorElement)) {
      event.preventDefault();
    }
    closeMobileMenu();
  });
});

document.querySelectorAll(".mobile-drawer a").forEach((el) => {
  el.addEventListener("click", () => closeMobileMenu());
});
