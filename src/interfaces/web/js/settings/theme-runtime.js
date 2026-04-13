function applyThemePreferences(preferences) {
  const theme = preferences.theme === "light" ? "light" : "dark";
  const fontFamily = preferences.font_family || "system-ui";
  const fontSize = Number(preferences.font_size || 16);
  const clampedFontSize = Math.max(12, Math.min(24, fontSize));
  const titleBarHeight = Number(preferences.title_bar_height || 56);
  const clampedTitleBarHeight = Math.max(40, Math.min(96, titleBarHeight));
  const titleBarFontSize = Number(preferences.title_bar_font_size || 20);
  const clampedTitleBarFontSize = Math.max(12, Math.min(40, titleBarFontSize));

  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.style.setProperty("--app-font-family", fontFamily);
  document.documentElement.style.setProperty("--app-font-size", `${clampedFontSize}px`);
  document.documentElement.style.setProperty("--mobile-titlebar-height", `${clampedTitleBarHeight}px`);
  document.documentElement.style.setProperty("--mobile-titlebar-font-size", `${clampedTitleBarFontSize}px`);
}

function loadThemePreferencesFromStorage() {
  applyThemePreferences({
    theme: localStorage.getItem("apmatia.theme") || "dark",
    font_family: localStorage.getItem("apmatia.font_family") || "system-ui",
    font_size: Number(localStorage.getItem("apmatia.font_size") || 16),
    title_bar_height: Number(localStorage.getItem("apmatia.title_bar_height") || 56),
    title_bar_font_size: Number(localStorage.getItem("apmatia.title_bar_font_size") || 20),
  });
}

loadThemePreferencesFromStorage();
