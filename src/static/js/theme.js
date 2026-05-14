const theme = {
  dark: "dark",
  light: "light",
};

function currentTheme() {
  var currTheme = localStorage.getItem("theme") ?? null;
  if (currTheme === null) {
    currTheme = theme.light;
    localStorage.setItem("theme", currTheme);
  }
  document.documentElement.setAttribute("data-theme", currTheme);
  return currTheme;
}

function toggleTheme() {
  const currTheme = currentTheme();
  const newTheme = currTheme === theme.dark ? theme.light : theme.dark;
  localStorage.setItem("theme", newTheme);
  document.documentElement.setAttribute("data-theme", newTheme);
  return newTheme;
}
