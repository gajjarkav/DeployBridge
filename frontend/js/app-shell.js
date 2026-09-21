const APP_THEME_KEY = "db_theme";
const APP_SIDEBAR_KEY = "db_sidebar_collapsed";
const APP_DEPLOYMENTS_KEY = "deploybridge_recent_deployments";

function getAuthSession() {
    return {
        token: localStorage.getItem("db_session_token"),
        dbSessionToken: localStorage.getItem("db_session_token"),
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
    if (!session.dbSessionToken) {
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
    
    // Sync any theme toggle checkboxes
    document.querySelectorAll("[data-theme-toggle], #themeToggle").forEach(btn => {
        if (btn.tagName === 'INPUT' && btn.type === 'checkbox') {
            btn.checked = storedTheme === "dark";
        }
    });
}

function bindThemeButton() {
    const buttons = document.querySelectorAll("[data-theme-toggle], #themeToggle");
    buttons.forEach((button) => {
        // Also handle change event if it's a checkbox
        const toggleTheme = (e) => {
            const currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
            const nextTheme = currentTheme === "dark" ? "light" : "dark";
            
            // If it's a checkbox/switch, keep it in sync
            if (button.tagName === 'INPUT' && button.type === 'checkbox') {
                button.checked = nextTheme === "dark";
            }

            localStorage.setItem(APP_THEME_KEY, nextTheme);
            updateThemeButtonLabel(nextTheme);

            if (!document.startViewTransition) {
                document.documentElement.setAttribute("data-theme", nextTheme);
                return;
            }

            // Get click coordinates or button center
            let x = window.innerWidth / 2;
            let y = window.innerHeight / 2;
            if (e && e.clientX && e.clientY) {
                x = e.clientX;
                y = e.clientY;
            } else if (button) {
                const rect = button.getBoundingClientRect();
                x = rect.left + rect.width / 2;
                y = rect.top + rect.height / 2;
            }

            const endRadius = Math.hypot(
                Math.max(x, window.innerWidth - x),
                Math.max(y, window.innerHeight - y)
            );

            const transition = document.startViewTransition(() => {
                document.documentElement.setAttribute("data-theme", nextTheme);
            });

            transition.ready.then(() => {
                document.documentElement.animate(
                    {
                        clipPath: [
                            `circle(0px at ${x}px ${y}px)`,
                            `circle(${endRadius}px at ${x}px ${y}px)`
                        ]
                    },
                    {
                        duration: 550,
                        easing: "ease-in-out",
                        pseudoElement: "::view-transition-new(root)",
                    }
                );
            });
        };

        button.addEventListener("click", (e) => {
            // Prevent default if it's a checkbox to let our custom logic handle it,
            // or just let it fire and update. For checkbox, 'change' is better but click is fine.
            if (button.tagName !== 'INPUT') toggleTheme(e);
        });
        button.addEventListener("change", (e) => {
            if (button.tagName === 'INPUT') toggleTheme(e);
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
    const appShell = document.getElementById("appShell");
    if (appShell) {
        appShell.classList.toggle("collapsed", collapsed);
    }
    
    // Sync any sidebar toggle checkboxes
    document.querySelectorAll("[data-sidebar-toggle], #sidebarToggle").forEach(btn => {
        if (btn.tagName === 'INPUT' && btn.type === 'checkbox') {
            btn.checked = collapsed;
        }
    });
}

function bindSidebarButtons() {
    const buttons = document.querySelectorAll("[data-sidebar-toggle], #sidebarToggle");
    buttons.forEach((button) => {
        const toggleSidebar = (e) => {
            let nextCollapsed;
            const appShell = document.getElementById("appShell");
            if (!appShell) return;

            if (button.tagName === 'INPUT' && button.type === 'checkbox') {
                nextCollapsed = button.checked;
            } else {
                nextCollapsed = !appShell.classList.contains("collapsed");
            }
            
            appShell.classList.toggle("collapsed", nextCollapsed);
            localStorage.setItem(APP_SIDEBAR_KEY, String(nextCollapsed));
        };

        button.addEventListener("click", (e) => {
            if (button.tagName !== 'INPUT') toggleSidebar(e);
        });
        button.addEventListener("change", (e) => {
            if (button.tagName === 'INPUT') toggleSidebar(e);
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
    localStorage.removeItem("db_session_token");
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
    try {
        const existing = JSON.parse(localStorage.getItem(APP_DEPLOYMENTS_KEY) || "[]");
        const next = [
            {
                ...entry,
                recordedAt: entry.recordedAt || new Date().toISOString(),
            },
            ...existing.filter(item => item.repository !== entry.repository || (new Date() - new Date(item.recordedAt) > 60000)),
        ].slice(0, 50);
        localStorage.setItem(APP_DEPLOYMENTS_KEY, JSON.stringify(next));
    } catch (e) {
        console.error("Failed to remember deployment:", e);
    }
}

function readRecentDeployments() {
    try {
        return JSON.parse(localStorage.getItem(APP_DEPLOYMENTS_KEY) || "[]");
    } catch (e) {
        console.error("Failed to read deployments:", e);
        return [];
    }
}


// Global Modals
window.showCustomAlert = function(title, message) {
    return new Promise((resolve) => {
        ensureCustomDialogDOM();
        const overlay = document.getElementById('db-custom-dialog-overlay');
        document.getElementById('custom-dialog-title').textContent = title;
        document.getElementById('custom-dialog-body').innerHTML = `<p>${(message || '').toString().replace(/\n/g, '<br>')}</p>`;
        
        const footer = document.getElementById('custom-dialog-footer');
        footer.innerHTML = `<button class="cd-btn cd-btn-primary" id="cd-btn-ok">OK</button>`;
        
        overlay.style.display = 'flex';
        
        document.getElementById('cd-btn-ok').onclick = () => {
            overlay.style.display = 'none';
            resolve();
        };
        
        document.querySelector('.custom-dialog-close').onclick = () => {
            overlay.style.display = 'none';
            resolve();
        };
    });
};

window.showCustomConfirm = function(title, message) {
    return new Promise((resolve) => {
        ensureCustomDialogDOM();
        const overlay = document.getElementById('db-custom-dialog-overlay');
        document.getElementById('custom-dialog-title').textContent = title;
        document.getElementById('custom-dialog-body').innerHTML = `<p>${(message || '').toString().replace(/\n/g, '<br>')}</p>`;
        
        const footer = document.getElementById('custom-dialog-footer');
        footer.innerHTML = `
            <button class="cd-btn cd-btn-secondary" id="cd-btn-cancel">Cancel</button>
            <button class="cd-btn cd-btn-primary" id="cd-btn-confirm">Confirm</button>
        `;
        
        overlay.style.display = 'flex';
        
        let resolved = false;
        
        document.getElementById('cd-btn-cancel').onclick = () => {
            if (resolved) return; resolved = true;
            overlay.style.display = 'none';
            resolve(false);
        };
        document.getElementById('cd-btn-confirm').onclick = () => {
            if (resolved) return; resolved = true;
            overlay.style.display = 'none';
            resolve(true);
        };
        document.querySelector('.custom-dialog-close').onclick = () => {
            if (resolved) return; resolved = true;
            overlay.style.display = 'none';
            resolve(false);
        };
    });
};

function ensureCustomDialogDOM() {
    if (document.getElementById('db-custom-dialog-overlay')) return;

    const style = document.createElement('style');
    style.innerHTML = `
        .custom-dialog-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(4px);
            z-index: 10000; display: flex; align-items: center; justify-content: center;
            padding: 20px;
        }
        .custom-dialog-container {
            background: var(--surface-color, #1e1e1e); border-radius: 12px;
            width: 100%; max-width: 500px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2); border: 1px solid var(--border-color, #333);
            display: flex; flex-direction: column; overflow: hidden;
            animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .custom-dialog-header {
            padding: 16px 24px; border-bottom: 1px solid var(--border-color, #333);
            background: var(--primary-light, #2a2a2a); display: flex;
            justify-content: space-between; align-items: center;
        }
        .custom-dialog-header h3 { font-family: 'Ubuntu', sans-serif; font-size: 1.2rem; color: var(--text-color, #fff); margin: 0; }
        .custom-dialog-close { background: transparent; border: none; font-size: 1.5rem; color: var(--text-muted, #aaa); cursor: pointer; line-height: 1; }
        .custom-dialog-body { padding: 24px; font-size: 0.95rem; color: var(--text-color, #fff); line-height: 1.5; max-height: 60vh; overflow-y: auto; }
        .custom-dialog-footer { padding: 16px 24px; border-top: 1px solid var(--border-color, #333); background: var(--surface-color, #1e1e1e); display: flex; justify-content: flex-end; gap: 12px; }
        .cd-btn { padding: 8px 16px; border-radius: 6px; font-family: 'Ubuntu', sans-serif; font-weight: 600; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; }
        .cd-btn-secondary { background: transparent; border: 1px solid var(--border-color, #333); color: var(--text-color, #fff); }
        .cd-btn-secondary:hover { background: var(--primary-light, #2a2a2a); }
        .cd-btn-primary { background: var(--primary-color, #3b82f6); border: 1px solid var(--primary-color, #3b82f6); color: var(--bg-color, #fff); }
        .cd-btn-primary:hover { opacity: 0.9; }
    `;
    document.head.appendChild(style);

    const overlay = document.createElement('div');
    overlay.id = 'db-custom-dialog-overlay';
    overlay.className = 'custom-dialog-overlay';
    overlay.style.display = 'none';
    overlay.innerHTML = `
        <div class="custom-dialog-container">
            <div class="custom-dialog-header">
                <h3 id="custom-dialog-title">Dialog</h3>
                <button class="custom-dialog-close">&times;</button>
            </div>
            <div class="custom-dialog-body" id="custom-dialog-body"></div>
            <div class="custom-dialog-footer" id="custom-dialog-footer"></div>
        </div>
    `;
    document.body.appendChild(overlay);
}
