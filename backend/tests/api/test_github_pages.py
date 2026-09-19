import pytest
import httpx
from unittest.mock import patch, AsyncMock
from src.core.crypto import encrypt_secret
from src.models.user import User
from src.schemas.github_pages import GitHubPagesDeployResponse

@pytest.mark.asyncio
@patch("src.services.github_pages.GitHubPagesService.detect")
async def test_detect_github_pages_profile(mock_detect, client: httpx.AsyncClient, auth_headers: dict):
    mock_detect.return_value = {
        "detected_profile": "html",
        "supported_profiles": ["html", "jekyll"],
        "reason": "Found index.html",
        "branch": "main",
        "recommended_platform": None
    }
    
    response = await client.post(
        "/v1/github-pages/detect",
        json={"owner": "test-owner", "repository": "test-repo"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["detected_profile"] == "html"
    assert data["branch"] == "main"

@pytest.mark.asyncio
@patch("src.services.deployment_service.DeploymentService.create_from_pages_deploy")
@patch("src.services.github_pages.GitHubPagesService.deploy")
async def test_deploy_to_github_pages(mock_deploy, mock_create_deployment, client: httpx.AsyncClient, auth_headers: dict):
    # Setup mock returns
    deploy_res = GitHubPagesDeployResponse(
        success=True,
        message="Deployed",
        resolved_profile="html",
        workflow_template="static.yml",
        branch="main"
    )
    mock_deploy.return_value = deploy_res
    mock_create_deployment.return_value = None

    response = await client.post(
        "/v1/github-pages/deploy",
        json={"owner": "test-owner", "repository": "test-repo", "deployment_profile": "html"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["resolved_profile"] == "html"

@pytest.mark.asyncio
@patch("src.services.github_pages.GitHubPagesService.add_custom_domain")
async def test_add_pages_custom_domain(mock_add_domain, client: httpx.AsyncClient, auth_headers: dict):
    mock_add_domain.return_value = {
        "domain": "example.com",
        "branch": "main",
        "cname_target": "test-owner.github.io",
        "record_type": "CNAME",
        "record_name": "example",
        "https_enabled": False,
        "status": "waiting_for_dns",
        "message": "Added CNAME file"
    }

    response = await client.post(
        "/v1/github-pages/custom-domains/test-owner/test-repo",
        json={"domain": "example.com", "branch": "main"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["domain"] == "example.com"

@pytest.mark.asyncio
@patch("src.services.github_pages.GitHubPagesService.verify_custom_domain")
async def test_verify_pages_custom_domain(mock_verify, client: httpx.AsyncClient, auth_headers: dict):
    mock_verify.return_value = {
        "domain": "example.com",
        "branch": "main",
        "cname_target": "test-owner.github.io",
        "record_type": "CNAME",
        "record_name": "example",
        "https_enabled": True,
        "status": "verified",
        "message": "Verified successfully"
    }

    response = await client.post(
        "/v1/github-pages/custom-domains/test-owner/test-repo/example.com/verify",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "verified"
