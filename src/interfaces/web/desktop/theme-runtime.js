function applyThemePreferences(preferences) {
  const theme = preferences.theme === "light" ? "light" : "dark";
  const fontFamily = preferences.font_family || "system-ui";
  const fontSize = Number(preferences.font_size || 16);
  const clampedFontSize = Math.max(12, Math.min(24, fontSize));

  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.style.setProperty("--app-font-family", fontFamily);
  document.documentElement.style.setProperty("--app-font-size", `${clampedFontSize}px`);
}

function loadThemePreferencesFromStorage() {
  applyThemePreferences({
    theme: localStorage.getItem("apmatia.theme") || "dark",
    font_family: localStorage.getItem("apmatia.font_family") || "system-ui",
    font_size: Number(localStorage.getItem("apmatia.font_size") || 16),
  });
}

loadThemePreferencesFromStorage();
