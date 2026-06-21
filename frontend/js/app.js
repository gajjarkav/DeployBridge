const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

window.onload = async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const githubCode = urlParams.get('code');

    if (githubCode) {
        await handleGitHubCallback(githubCode);
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
        console.error("Failed to get login URL: ", error);
        alert(`Failed to connect to backend at ${BACKEND_API_URL}. Please ensure the backend server is running and accessible.`);
    }
});

async function handleGitHubCallback(code) {
    try {
        window.history.replaceState({}, document.title, window.location.pathname);

        const response = await fetch(`${BACKEND_API_URL}/auth/callback?code=${code}`);
        const data = await response.json();

        localStorage.setItem("gh_access_token", data.github_access_token);
        localStorage.setItem("gh_username", data.user.username);
        localStorage.setItem("gh_avatar", data.user.avatar_url);

        showDashboard();
    } catch (error) {
        console.error("Failed to complete login callback:", error);
    }
}

function checkExistingSession() {
    const token = localStorage.getItem("gh_access_token");
    if (token) {
        showDashboard();
    } else {
        document.getElementById("auth-section").style.display = "block";
        document.getElementById("dashboard-section").style.display = "none";
    }
}

async function showDashboarrd() {

    document.getElementById("auth-section").style.display = "none";
    document.getElementById("dashboard-section").style.display = "block";

    document.getElementById("user-name").innerText = localStorage.getItem("gh_username");
    document.getElementById("user-avatar").src = localStorage.getItem("gh_avatar");

    await fetchAndRenderRepos();
}

async function fetchAndRenderRepos() {
    const token = localStorage.getItem("gh_access_token");
    
    try {
        const response = await fetch("https://api.github.com/user/repos?sort=updated&per_page=10", {
            headers: {
                "Authorization": `Bearer ${token}`,
                "Accept": "application/vnd.github.v3+json"
            }
        });

        const repos = await response.json();
        const repoListElement = document.getElementById("repo-list");
        repoListElement.innerHTML = '';

        repos.forEach(repo => {
            const li = document.createElement('li');
            li.innerHTML = `<a href="${repo.html_url}" target="_blank">${repo.name}</a> - ${repo.visibility}`;
            repoListElement.appendChild(li);
        });
    }   catch (error) {
        console.error("Failed to fetch repositories:", error);
        document.getElementById("repo-list").innerHTML = '<li> Error  loading repositories. </li>';
    }
}

document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("gh_access_token");
    localStorage.removeItem("gh_username");
    localStorage.removeItem("gh_avatar");

    window.location.reload();
})