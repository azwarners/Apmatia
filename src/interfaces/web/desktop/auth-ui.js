async function logoutApmatia() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (error) {
    // best effort logout; continue to login either way
  }
  window.location.href = "/login";
}

document.querySelectorAll(".logout-action").forEach((el) => {
  el.addEventListener("click", logoutApmatia);
});
