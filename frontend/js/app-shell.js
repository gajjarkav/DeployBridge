const APP_THEME_KEY = "deploybridge_theme";
const APP_SIDEBAR_KEY = "deploybridge_sidebar_collapsed";
const APP_DEPLOYMENTS_KEY = "deploybridge_recent_deployments";

function getAuthSession() {
    return {
        token: localStorage.getItem("gh_access_token"),
        username: localStorage.getItem("gh_username"),
        avatar: localStorage.getItem("gh_avatar"),
        email: localStorage.getItem("gh_email"),
        userId: localStorage.getItem("gh_user_id"),
        scope: localStorage.getItem("gh_scope"),
        tokenType: localStorage.getItem("gh_token_type") || "Bearer",
        lastLogin: localStorage.getItem("gh_last_login"),
    };
}

function requireAuthSession() {
    const session = getAuthSession();
    if (!session.token) {
        window.location.href = "../templates/auth.html";
        return null;
    }
    return session;
}

function initializeAppShell(activePage) {
    const session = requireAuthSession();
    if (!session) {
        return null;
    }

    applySavedTheme();
    applySavedSidebarState();
    hydrateUser(session);
    bindThemeButton();
    bindSidebarButtons();
    bindLogoutButtons();
    highlightActiveNav(activePage);

    return session;
}

function applySavedTheme() {
    const storedTheme = localStorage.getItem(APP_THEME_KEY) || "light";
    document.documentElement.setAttribute("data-theme", storedTheme);
    updateThemeButtonLabel(storedTheme);
}

function bindThemeButton() {
    const buttons = document.querySelectorAll("[data-theme-toggle]");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
            const nextTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", nextTheme);
            localStorage.setItem(APP_THEME_KEY, nextTheme);
            updateThemeButtonLabel(nextTheme);
        });
    });
}

function updateThemeButtonLabel(theme) {
    const labels = document.querySelectorAll("[data-theme-label]");
    labels.forEach((label) => {
        label.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    });
}

function applySavedSidebarState() {
    const collapsed = localStorage.getItem(APP_SIDEBAR_KEY) === "true";
    document.body.classList.toggle("sidebar-collapsed", collapsed);
}

function bindSidebarButtons() {
    const buttons = document.querySelectorAll("[data-sidebar-toggle]");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const nextCollapsed = !document.body.classList.contains("sidebar-collapsed");
            document.body.classList.toggle("sidebar-collapsed", nextCollapsed);
            localStorage.setItem(APP_SIDEBAR_KEY, String(nextCollapsed));
        });
    });
}

function hydrateUser(session) {
    document.querySelectorAll("[data-user-name]").forEach((node) => {
        node.textContent = session.username || "GitHub User";
    });
    document.querySelectorAll("[data-user-avatar]").forEach((node) => {
        node.src = session.avatar || "";
        node.alt = session.username ? `${session.username} avatar` : "User avatar";
    });
}

function bindLogoutButtons() {
    document.querySelectorAll("[data-logout]").forEach((button) => {
        button.addEventListener("click", logoutUser);
    });
}

function logoutUser() {
    localStorage.removeItem("gh_access_token");
    localStorage.removeItem("gh_username");
    localStorage.removeItem("gh_avatar");
    localStorage.removeItem("gh_email");
    localStorage.removeItem("gh_user_id");
    localStorage.removeItem("gh_scope");
    localStorage.removeItem("gh_token_type");
    localStorage.removeItem("gh_last_login");
    window.location.href = "../templates/auth.html";
}

function highlightActiveNav(activePage) {
    document.querySelectorAll("[data-nav]").forEach((link) => {
        link.classList.toggle("active", link.dataset.nav === activePage);
    });
}

function rememberDeployment(entry) {
    const existing = JSON.parse(localStorage.getItem(APP_DEPLOYMENTS_KEY) || "[]");
    const next = [
        {
            ...entry,
            recordedAt: new Date().toISOString(),
        },
        ...existing,
    ].slice(0, 8);
    localStorage.setItem(APP_DEPLOYMENTS_KEY, JSON.stringify(next));
}

function readRecentDeployments() {
    return JSON.parse(localStorage.getItem(APP_DEPLOYMENTS_KEY) || "[]");
}
