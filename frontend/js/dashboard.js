
window.onload = async () => {
    const token = localStorage.getItem("gh_access_token");

    if (!token) {
        window.location.href = '../templates/auth.html';
        return;
    }

    const userNameEl = document.getElementById("user-name");
    const userAvatarEl = document.getElementById("user-avatar");

    if (userNameEl) userNameEl.innerText = localStorage.getItem("gh_username");
    if (userAvatarEl) userAvatarEl.src = localStorage.getItem("gh_avatar");

    await fetchAndRenderRepos(token);
};

async function fetchAndRenderRepos(token) {
    try {
        const response = await fetch("https://api.github.com/user/repos", {
            headers: {
                "Authorization": `Bearer ${token}`            }
        });

        if (!response.ok) {
            throw new Error("Failed to fetch repos, Token might be expired.");
        }

        const repos = await response.json();
        const getStatus = (repo) => {
            if (repo.archived) return "Archived";
            if (repo.disabled) return "Disabled";
            return "Active";
        }
        
        const getRelativeTime = (dateString) => {
            const date = new Date(dateString);
            const now = new Date();
            const seconds = Math.floor((now - date) / 1000);

            if (seconds < 60) return 'Just now';
            const minutes = Math.floor(seconds / 60);
            if (minutes < 60) return `${minutes}m ago`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}h ago`;
            const days = Math.floor(hours / 24);
            if (days < 30) return `${days}d ago`;
            const months = Math.floor(days / 30);
            if (months / 12) return `${months}mo ago`;
            const years = Math.floor(months / 12);
            return `${year}y ago`;
        }
        const tableBody = document.getElementById("repo-table-body");
        tableBody.innerHTML = '';

        repos.forEach((repo, index) => {
            const tr =document.createElement("tr");

            const updatedAt = new Date(repo.updated_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric"
            });

            const status = repo.archived ? "Archived" : (repo.disabled ? "Disabled" : "Active");
            const statusColor = repo.archived ? '#ffebee' : '#e0ece4';
            const statusTextColor = repo.archived ? '#c62828' : '#2e7d32';

            tr.innerHTML = `
                <td style="padding: 8px;">${index + 1}</td>
                <td style="padding: 8px;"><a href="${repo.url}" target="_blank" style="text-decoration: none; color: blue;">${repo.name}</a></td>
                <td style="padding: 8px;">${repo.language}</td>
                <td style="padding: 8px;">${repo.visibility}</td>
                <td style="padding: 8px;">
                    <span style="background-color: ${statusColor}; color: ${statusTextColor}; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                        ${status}
                    </span>
                </td>
                <td style="padding: 8px; font-size: 13px; color: #586069;">
                    <div title="${updatedAt}">${getRelativeTime(repo.updated_at)}</div>
                </td>
                <td style="padding: 8px;">
                    <a href="${repo.html_url}" target="_blank" style="text-decoration: none;">
                        <button style="cursor: pointer; padding: 4px 12px; background-color: #0366d6; color: white; border: none; border-radius: 4px;">
                            View Repo
                        </button>
                    </a>
                </td>
                <td style="padding: 8px;">
                    <div style="display: flex; gap: 8px;">

                <button
                    onclick="analyzeRepo('${repo.name}')"
                    style="cursor:pointer;padding:4px 12px;background:#6c757d;color:white;border:none;border-radius:4px;font-size:12px;"
                >
                    Analyze
                </button>

                <button
                    onclick="deployGitHubPages('${repo.owner.login}','${repo.name}')"
                    style="cursor:pointer;padding:4px 12px;background:#7c3aed;color:white;border:none;border-radius:4px;font-size:12px;"
                >
                    GitHub Pages
                </button>

            </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });

    } catch (error) {
        console.error("Error: ", error);
        document.getElementById("repo-table-body").innerHTML = '<tr><td colspan="6" style="color:red; text-align: center; padding: 8px;">Error loading repositories.</td></tr>';
    }
}

window.analyzeRepo = (repoName) => {
    alert(`Initalitiong deep scan for: ${repoName}...\n\n(Backend hit!!)`);
    console.log(`Scan triggered for ${repoName}`);
}

window.deployGitHubPages = async (owner, repository) => {

    const confirmed = confirm(
        `Deploy "${repository}" to GitHub Pages?`
    );

    if (!confirmed) {
        return;
    }

    const token = localStorage.getItem("gh_access_token");

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/v1/github-pages/deploy",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                },

                body: JSON.stringify({
                    owner,
                    repository,
                }),
            }
        );

        const data = await response.json();

        alert(data.message);

    } catch (error) {

        console.error(error);

        alert("Deployment failed.");

    }

}

document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("gh_access_token");
    localStorage.removeItem("gh_username");
    localStorage.removeItem("gh_avatar");

    window.location.href = "../templates/auth.html";
})