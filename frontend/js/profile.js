window.onload = async () => {
    const session = initializeAppShell("profile");
    if (!session) return;

    const token = localStorage.getItem("gh_access_token");
    if (!token) {
        window.location.href = "../templates/auth.html";
        return;
    }

    const profileName = document.getElementById("profile-name");
    const profileAvatar = document.getElementById("profile-avatar");
    const profileBadge = document.getElementById("profile-badge");
    const profileBio = document.getElementById("profile-bio");
    const profileWebsite = document.getElementById("profile-website");
    const profileLocation = document.getElementById("profile-location");
    const profileCompany = document.getElementById("profile-company");
    const detailLogin = document.getElementById("detail-login");
    const detailGithubId = document.getElementById("detail-github-id");
    const detailEmail = document.getElementById("detail-email");
    const detailType = document.getElementById("detail-type");
    const detailTokenType = document.getElementById("detail-token-type");
    const detailScope = document.getElementById("detail-scope");
    const detailLastLogin = document.getElementById("detail-last-login");
    const detailToken = document.getElementById("detail-token");
    const detailCreatedAt = document.getElementById("detail-created-at");
    const detailUpdatedAt = document.getElementById("detail-updated-at");
    const detailRepoVisibility = document.getElementById("detail-repo-visibility");
    const statTotal = document.getElementById("stat-total");
    const statPublic = document.getElementById("stat-public");
    const statPrivate = document.getElementById("stat-private");
    const statFollowers = document.getElementById("stat-followers");
    const statFollowing = document.getElementById("stat-following");

    try {
        const response = await fetch("https://api.github.com/user", {
            headers: {
                Authorization: `Bearer ${token}`,
                Accept: "application/vnd.github+json",
            },
        });

        if (!response.ok) {
            throw new Error("Failed to fetch GitHub profile.");
        }

        const user = await response.json();

        const displayName = user.name || user.login || session.username || "GitHub User";
        const safeAvatar = user.avatar_url || session.avatar || "https://placehold.co/120x120/e0e0e0/000000?text=U";
        const sessionToken = localStorage.getItem("gh_access_token") || "";
        const maskedToken = sessionToken
            ? `${sessionToken.slice(0, 6)}...${sessionToken.slice(-4)}`
            : "Not available";

        if (profileName) profileName.textContent = displayName;
        if (profileAvatar) profileAvatar.src = safeAvatar;
        if (profileBadge) profileBadge.textContent = user.type || "User";
        if (profileBio) profileBio.textContent = user.bio || "No public bio provided for this GitHub account yet.";
        if (profileWebsite) {
            const website = user.blog && user.blog.trim();
            profileWebsite.href = website || "#";
            profileWebsite.textContent = website ? "Website" : "No website";
            profileWebsite.style.pointerEvents = website ? "auto" : "none";
            profileWebsite.style.opacity = website ? "1" : "0.6";
        }
        if (profileLocation) profileLocation.textContent = user.location || "Location unavailable";
        if (profileCompany) profileCompany.textContent = user.company || "Company unavailable";

        if (detailLogin) detailLogin.textContent = `@${user.login || session.username || "github-user"}`;
        if (detailGithubId) detailGithubId.textContent = user.id ? String(user.id) : "Unknown";
        if (detailEmail) detailEmail.textContent = user.email || localStorage.getItem("gh_email") || "Private";
        if (detailType) detailType.textContent = user.type || "User";
        if (detailTokenType) detailTokenType.textContent = (localStorage.getItem("gh_token_type") || "Bearer").toUpperCase();
        if (detailScope) detailScope.textContent = localStorage.getItem("gh_scope") || "read:user repo workflow";

        const lastLogin = localStorage.getItem("gh_last_login");
        if (detailLastLogin) {
            detailLastLogin.textContent = lastLogin
                ? new Date(lastLogin).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
                : "Not available";
        }

        if (detailToken) detailToken.textContent = maskedToken;
        if (detailCreatedAt) detailCreatedAt.textContent = user.created_at ? new Date(user.created_at).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" }) : "Unknown";
        if (detailUpdatedAt) detailUpdatedAt.textContent = user.updated_at ? new Date(user.updated_at).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" }) : "Unknown";

        const totalRepos = Number(user.public_repos || 0) + Number(user.total_private_repos || 0);
        if (statTotal) statTotal.textContent = String(totalRepos);
        if (statPublic) statPublic.textContent = String(user.public_repos || 0);
        if (statPrivate) statPrivate.textContent = user.total_private_repos !== undefined ? String(user.total_private_repos) : "N/A";
        if (statFollowers) statFollowers.textContent = String(user.followers || 0);
        if (statFollowing) statFollowing.textContent = String(user.following || 0);

        const visibilityLabel = [
            user.public_repos ? `${user.public_repos} Public` : "No public repos",
            user.total_private_repos !== undefined ? `${user.total_private_repos} Private` : "Private count unavailable"
        ].join(" • ");
        if (detailRepoVisibility) detailRepoVisibility.textContent = visibilityLabel;

        const sessionStatus = document.getElementById("detail-session-status");
        if (sessionStatus) {
            sessionStatus.innerHTML = '<span class="status-pill">Active</span>';
        }
    } catch (error) {
        console.error("Profile fetch error:", error);

        if (profileName) profileName.textContent = session.username || "GitHub User";
        if (profileBio) profileBio.textContent = "Unable to load the most recent GitHub profile data right now.";
        if (detailToken) detailToken.textContent = "Unavailable";
        if (detailScope) detailScope.textContent = localStorage.getItem("gh_scope") || "Unknown";
        if (detailLastLogin) detailLastLogin.textContent = localStorage.getItem("gh_last_login") || "Unknown";
        if (profileBadge) profileBadge.textContent = "Error";
        if (profileBadge) profileBadge.classList.add("warn");
    }
};
