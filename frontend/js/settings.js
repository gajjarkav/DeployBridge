window.onload = async () => {
    const session = initializeAppShell("settings");
    if (!session) {
        return;
    }

    document.getElementById("settings-username").textContent = session.username || "GitHub User";
    document.getElementById("settings-token-status").textContent = session.token ? "Active local session" : "Missing session";
    document.getElementById("settings-theme").textContent = document.documentElement.getAttribute("data-theme") || "light";
};
