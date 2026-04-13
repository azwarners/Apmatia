const usernameEl = document.getElementById("auth-username");
const passwordEl = document.getElementById("auth-password");
const submitEl = document.getElementById("auth-submit");
const statusEl = document.getElementById("auth-status");
const modeLabelEl = document.getElementById("auth-mode-label");

let mode = "login";

function setStatus(text) {
  statusEl.innerText = text;
}

function applyMode(nextMode) {
  mode = nextMode === "register" ? "register" : "login";
  if (mode === "register") {
    modeLabelEl.innerText = "Create your first account";
    submitEl.innerText = "Create Account";
  } else {
    modeLabelEl.innerText = "Sign in";
    submitEl.innerText = "Sign in";
  }
}

async function loadSession() {
  try {
    const response = await fetch("/api/auth/session");
    if (!response.ok) {
      setStatus("Unable to check session.");
      applyMode("login");
      return;
    }
    const snapshot = await response.json();
    if (snapshot.authenticated) {
      window.location.href = "/";
      return;
    }

    applyMode(snapshot.has_users ? "login" : "register");
    setStatus(snapshot.has_users ? "Sign in to continue." : "Create your first account.");
  } catch (error) {
    applyMode("login");
    setStatus("Unable to check session.");
  }
}

async function submitAuth() {
  const username = (usernameEl.value || "").trim();
  const password = passwordEl.value || "";
  if (!username || !password) {
    setStatus("Username and password are required.");
    return;
  }

  submitEl.disabled = true;
  setStatus(mode === "register" ? "Creating account..." : "Signing in...");
  try {
    const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      setStatus(err.detail || "Authentication failed.");
      submitEl.disabled = false;
      return;
    }
    window.location.href = "/";
  } catch (error) {
    setStatus("Authentication failed.");
    submitEl.disabled = false;
  }
}

submitEl.addEventListener("click", submitAuth);
passwordEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    submitAuth();
  }
});

loadSession();
