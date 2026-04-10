const aiSettingsEl = document.getElementById("ai-settings");
const discussionSettingsEl = document.getElementById("discussion-settings");
const themeSettingsEl = document.getElementById("theme-settings");
const saveButtonEl = document.getElementById("save-button");
const statusEl = document.getElementById("status");

let initialSettings = null;

function setStatus(text) {
  statusEl.innerText = text;
}

function currentFormValues() {
  return {
    ...aiSettingsEl.getValues(),
    ...discussionSettingsEl.getValues(),
    ...themeSettingsEl.getValues(),
  };
}

function applyThemeLocally(values) {
  const themeValues = {
    theme: values.theme || "dark",
    font_family: values.font_family || "system-ui",
    font_size: Number(values.font_size || 16),
  };
  localStorage.setItem("apmatia.theme", themeValues.theme);
  localStorage.setItem("apmatia.font_family", themeValues.font_family);
  localStorage.setItem("apmatia.font_size", String(themeValues.font_size));
  if (typeof applyThemePreferences === "function") {
    applyThemePreferences(themeValues);
  }
}

function refreshDirtyState() {
  if (!initialSettings) {
    saveButtonEl.disabled = true;
    return;
  }
  const current = currentFormValues();
  const isDirty = JSON.stringify(current) !== JSON.stringify(initialSettings);
  saveButtonEl.disabled = !isDirty;
  if (isDirty) {
    setStatus("Unsaved changes.");
  } else {
    setStatus("All changes saved.");
  }
}

async function loadSettings() {
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) {
      setStatus("Failed to load settings.");
      return;
    }
    const settings = await response.json();
    aiSettingsEl.setValues({
      model_url: settings.model_url || "",
      max_response_size: settings.max_response_size || 8192,
    });
    discussionSettingsEl.setValues({
      system_prompt: settings.system_prompt || "",
    });
    themeSettingsEl.setValues({
      theme: settings.theme || "dark",
      font_family: settings.font_family || "system-ui",
      font_size: settings.font_size || 16,
    });
    applyThemeLocally(settings);
    initialSettings = currentFormValues();
    refreshDirtyState();
  } catch (error) {
    setStatus("Failed to load settings.");
  }
}

async function saveSettings() {
  if (saveButtonEl.disabled) {
    return;
  }
  const payload = currentFormValues();
  if (!payload.model_url) {
    setStatus("Model URL is required.");
    return;
  }
  if (!Number.isInteger(payload.max_response_size) || payload.max_response_size < 1) {
    setStatus("Max response size must be a positive integer.");
    return;
  }
  if (payload.theme !== "dark" && payload.theme !== "light") {
    setStatus("Theme must be dark or light.");
    return;
  }
  if (!Number.isInteger(payload.font_size) || payload.font_size < 12 || payload.font_size > 24) {
    setStatus("Font size must be an integer from 12 to 24.");
    return;
  }

  saveButtonEl.disabled = true;
  setStatus("Saving settings...");
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json();
      setStatus(`Failed to save settings: ${err.detail || response.statusText}`);
      refreshDirtyState();
      return;
    }
    initialSettings = payload;
    applyThemeLocally(payload);
    refreshDirtyState();
  } catch (error) {
    setStatus("Failed to save settings.");
    refreshDirtyState();
  }
}

aiSettingsEl.addEventListener("change", refreshDirtyState);
discussionSettingsEl.addEventListener("change", refreshDirtyState);
themeSettingsEl.addEventListener("change", () => {
  applyThemeLocally(currentFormValues());
  refreshDirtyState();
});

loadSettings();
