const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

window.onload = async () => {

    if (localStorage.getItem("gh_access_token")) {
        window.location.href = "../templates/dashboard.html";
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const githubCode = urlParams.get('code');

    if (githubCode) {
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

        if (data.login_url) {
            window.location.href = data.login_url;
        } else {
            alert("Backend succeeded but did not return 'login_url'. check browser console log.");
        }
    }  catch (error) {
        alert(`Failed to connect to backend at ${BACKEND_API_URL}. Please ensure the backend server is running and accessible.`);
    }
});

function checkExistingSession() {
    const token = localStorage.getItem("gh_access_token");
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

        localStorage.setItem("gh_access_token", data.github_access_token);
        localStorage.setItem("gh_username", data.user.username);
        localStorage.setItem("gh_avatar", data.user.avatar_url);

        window.location.href = '../templates/dashboard.html';
    } catch (error) {
        console.error("Login failed: ", error);
        alert("Authentication failed. Please try agein.");
        window.location.reload();
    }
}
