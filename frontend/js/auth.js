const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

window.onload = async () => {
    applySavedTheme();
    bindThemeButton();
    if (localStorage.getItem("db_session_token")) {
        window.location.href = "../templates/dashboard.html";
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const githubCode = urlParams.get('code');
    const githubState = urlParams.get('state');

    if (githubCode) {
        const savedState = sessionStorage.getItem("oauth_state");
        if (!savedState || savedState !== githubState) {
            alert("OAuth state mismatch. Security check failed. Please try logging in again.");
            sessionStorage.removeItem("oauth_state");
            window.location.href = window.location.pathname;
            return;
        }
        sessionStorage.removeItem("oauth_state");

        const loginBtn = document.getElementById("login-btn");
        const loadingText = document.getElementById("loading-text");

        if (loginBtn) loginBtn.style.display = "none";
        if (loadingText) loadingText.style.display = "block";

        await handleGitHubCallback(githubCode)
    } else {
        checkExistingSession();
    }
};

document.getElementById('login-btn').addEventListener('click', async () => {
    try {

        const response = await fetch(`${BACKEND_API_URL}/auth/login`);

        if (!response.ok) {
            const errorText = await response.text();
            alert(`Backend Error: (${response.status}): ${errorText}`);
            return;
        }

        const data = await response.json();
        console.log("Data received from backend: ", data);

        if (data.login_url && data.state) {
            sessionStorage.setItem("oauth_state", data.state);
            window.location.href = data.login_url;
        } else {
            alert("Backend succeeded but did not return 'login_url' or 'state'. check browser console log.");
        }
    } catch (error) {
        alert(`Failed to connect to backend at ${BACKEND_API_URL}. Please ensure the backend server is running and accessible.`);
    }
});

function checkExistingSession() {
    const token = localStorage.getItem("db_session_token");
    if (token) {
        window.location.href = "../templates/dashboard.html";
    } else {
        document.getElementById("auth-section").style.display = "block";
        document.getElementById("dashboard-section").style.display = "none";
    }
}

async function handleGitHubCallback(code) {
    try {
        window.history.replaceState({}, document.title, window.location.pathname);

        const response = await fetch(`${BACKEND_API_URL}/auth/callback?code=${code}`);

        const data = await response.json();

        localStorage.setItem("db_session_token", data.session_token || "");
        localStorage.setItem("gh_username", data.user.username || "");
        localStorage.setItem("gh_avatar", data.user.avatar_url || "");
        localStorage.setItem("gh_email", data.user.email || "");
        localStorage.setItem("gh_user_id", data.user.id || "");
        localStorage.setItem("gh_scope", data.scope || "");
        localStorage.setItem("gh_token_type", data.token_type || "bearer");
        localStorage.setItem("gh_last_login", data.last_login || new Date().toISOString());

        window.location.href = '../templates/dashboard.html';
    } catch (error) {
        console.error("Login failed: ", error);
        alert("Authentication failed. Please try again.");
        window.location.reload();
    }
}
