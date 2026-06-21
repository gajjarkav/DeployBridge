window.onload = async () => {
    const token = localStorage.getItem("gh_access_token");

    if (!token) {
        window.location.href = '../templates/auth.html';
        return;
    }

    document.getElementById("user-name").innerText = localStorage.getItem("gh_username");
    document.getElementById("user-avatar").src = localStorage.getItem("gh_avatar");

    await fetchAndRenderRepos(token);
};

async function fetchAndRenderRepos(token) {
    try {
        const response = await fetch("https://api.github.com/user/repos?sort=updates&per_page=10", {
            headers: {
                "Authorization": `Bearer ${token}`,
                "Accept": "application/vnd.github.com.v3+json"
            }
        });

        if (!response.ok) {
            throw new Error("Failed to fetch repos, Token might be expired.");
        }

        const repos = await response.json();
        const repoListElement = document.getElementById("repo-list");
        repoListElement.innerHTML = "";

        repos.forEach(repo => {
            const li = document.createElement("li");
            li.innerHTML = `<a href="${repo.html_url}" target="_blank">${repo.name}</a> (${repo.visibility})`;
            repoListElement.appendChild(li);
        });
    } catch (error) {
        console.error("Error: ", error);
        document.getElementById("repo-list").innerHTML = '<li style="color:red;">Error loading repositories. Please try logging in again.</li>';
    }
}

document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("gh_access_token");
    localStorage.removeItem("gh_username");
    localStorage.removeItem("gh_avatar");

    window.location.href = "../templates/auth.html";
})