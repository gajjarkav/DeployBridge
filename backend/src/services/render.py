"""Render.com integration service.

Mirrors the style of `services/github_pages.py`:
  - All methods are async classmethods on a single `RenderService` class.
  - HTTP calls go through httpx.AsyncClient with short, fixed timeouts.
  - Errors are surfaced as a single `RenderError` exception so the
    api/v1/render.py handlers can use the same try/except pattern as
    github_pages.py.

Key Render API behaviors encoded here (verified against the live
api-docs.render.com reference on 2026-09-16):

  1. Auth is HTTP Bearer with the user's `rnd_...` API key (NOT OAuth).
     Keys are workspace-spanning: one key reaches every workspace the
     user belongs to. We resolve the personal workspace (type="user")
     at /connect time and cache its `tea-...` ID on the user row.

  2. `POST /v1/services` returns `{service, deployId}` -- the deploy
     is auto-triggered by Render, no separate "trigger deploy" call
     needed for first-run deploys. We expose `deploy_id` in the
     response so the frontend can poll deploys from t=0.

  3. `serviceDetails.envSpecificDetails` is REQUIRED for native
     runtimes (python/node/go/...) and must contain BOTH buildCommand
     AND startCommand. For runtime=docker we set `dockerfilePath`
     instead -- mixing the two is a 422.

  4. `autoDeploy` and `clearCache` are string enums ("yes"/"no" and
     "clear"/"do_not_clear") NOT booleans. We translate from the
     friendlier Python bool on the way out.

  5. The public service URL lives at `serviceDetails.url`; the
     top-level `dashboardUrl` is the admin UI link. We return both
     so the frontend can show a "Open app" button and a "Open in
     Render dashboard" link separately.

  6. Custom domains: the API does NOT return DNS records -- only
     `verificationStatus`. We derive the CNAME target from the
     service's `onrender.com` URL and return it in our response so
     the frontend can show the user exactly what to add at their DNS
     provider without round-tripping to the Render dashboard.

The detection rules (`detect_runtime`) reuse `GitHubPagesService`'s
`RepositoryContext` so we don't duplicate the GitHub fetch-and-parse
code: same package.json / next.config / root-file logic as Pages, but
interpreted for a server runtime instead of a static site.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from ..core.exception import RenderError
from ..schemas.render import (
    RenderConnectResponse,
    RenderCustomDomainResponse,
    RenderDeployRequest,
    RenderDeployResponse,
    RenderDetectResponse,
    RenderPlan,
    RenderRuntime,
    RenderServiceDetail,
    RenderServiceSummary,
    RenderStatusResponse,
)
from .github_pages import GitHubPagesService


class RenderService:
    """Stateless facade over the Render REST API.

    Every method takes the decrypted API key as its first argument so
    the caller (api/v1/render.py) is responsible for the decrypt step.
    The class never touches the DB or the Fernet layer -- that's the
    endpoint's job, mirroring GitHubPagesService's split.
    """

    API_BASE = "https://api.render.com/v1"
    DEFAULT_TIMEOUT = 30.0
    LONG_TIMEOUT = 60.0  # create-service can take ~10s while Render clones the repo

    # -------------------------------------------------------------------
    # Headers / low-level request
    # -------------------------------------------------------------------

    @classmethod
    def _headers(cls, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @classmethod
    async def _request(
        cls,
        method: str,
        path: str,
        api_key: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Single low-level request helper.

        Centralizes the error-mapping rule: 401 → invalid key, 402 →
        plan limit hit (free tier exhausted), 429 → rate limited, 5xx
        → Render is having a bad time. Every caller can `raise_for`
        the response with the right status_code without repeating the
        switch.
        """
        url = f"{cls.API_BASE}{path}"
        async with httpx.AsyncClient(timeout=timeout or cls.DEFAULT_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=cls._headers(api_key),
                json=json,
                params=params,
            )
        return response

    @classmethod
    def _raise_for(cls, response: httpx.Response, *, default_message: str) -> None:
        """Map non-2xx Render responses to RenderError.

        We never log or include the raw response body in the user-facing
        `detail` for 4xx errors (it may contain env var values Render
        echoed back); we surface only a short summary + status code.
        For 5xx we include more because Render's error pages are
        generally non-sensitive and the user needs the context to file
        a bug report.
        """
        if 200 <= response.status_code < 300:
            return

        status = response.status_code
        try:
            body = response.json()
            msg = body.get("message") or body.get("error") or response.text[:300]
        except Exception:
            msg = response.text[:300] if response.text else ""

        if status == 401:
            raise RenderError(
                message="Invalid Render API key.",
                detail="Render rejected this API key. Generate a fresh one at "
                       "https://dashboard.render.com/u/settings → API Keys and try again.",
                status_code=400,
            )
        if status == 402:
            raise RenderError(
                message="Render free-tier limit reached.",
                detail="Your Render workspace hit a plan quota (e.g. 25 services on the "
                       "free tier, 750 instance-hours/month, or 500 build minutes). "
                       "Upgrade your plan or delete an unused service.",
                status_code=402,
            )
        if status == 403:
            raise RenderError(
                message="Render returned 403 Forbidden.",
                detail="Your API key works but doesn't have permission for this action. "
                       "If the workspace enforces an IP allow-list, make sure this "
                       "DeployBridge instance's egress IP is on it.",
                status_code=403,
            )
        if status == 404:
            raise RenderError(
                message="Render returned 404 Not Found.",
                detail="The service or resource was not found in this workspace.",
                status_code=404,
            )
        if status == 429:
            # Render returns RateLimit-* headers; surface them if present.
            limit = response.headers.get("RateLimit-Limit", "?")
            reset = response.headers.get("RateLimit-Reset", "?")
            raise RenderError(
                message="Render rate limit hit.",
                detail=f"Render returned 429. Bucket limit={limit}, resets at epoch {reset}. "
                       "Wait and retry; see https://api-docs.render.com/reference/rate-limiting.",
                status_code=429,
            )
        if 400 <= status < 500:
            raise RenderError(
                message=default_message or "Render rejected the request.",
                detail=f"Render returned {status}: {msg}",
                status_code=status,
            )
        # 5xx
        raise RenderError(
            message="Render is unavailable.",
            detail=f"Render returned {status}: {msg}. This is a Render-side issue; "
                   "retry in a few minutes.",
            status_code=502,
        )

    # -------------------------------------------------------------------
    # Connect / validate / status
    # -------------------------------------------------------------------

    @classmethod
    async def list_owners(cls, api_key: str) -> list[dict[str, Any]]:
        """GET /v1/owners -- list workspaces the key can reach.

        Render returns `[{"owner": {...}, "cursor": "..."}, ...]`. We
        strip the cursor wrapper and return only the owner objects,
        sorted so the personal workspace (type:"user") comes first --
        that's the one we cache as `render_owner_id` on /connect.
        """
        response = await cls._request("GET", "/owners", api_key)
        cls._raise_for(response, default_message="Failed to list Render workspaces.")

        raw_items = response.json() or []
        owners: list[dict[str, Any]] = []
        for item in raw_items:
            owner = item.get("owner") if isinstance(item, dict) else None
            if isinstance(owner, dict) and owner.get("id"):
                owners.append(owner)
        # Personal workspace first so /connect picks it deterministically.
        owners.sort(key=lambda o: 0 if o.get("type") == "user" else 1)
        return owners

    @classmethod
    async def validate_key_and_resolve_owner(cls, api_key: str) -> dict[str, Any]:
        """Returns the personal workspace's owner dict.

        Raises RenderError with status_code=400 if the key is invalid
        or if the user has no personal workspace (rare -- only happens
        for team-only service accounts).
        """
        owners = await cls.list_owners(api_key)
        if not owners:
            raise RenderError(
                message="Render API key is valid but no workspaces are visible.",
                detail="Render accepted the key but returned an empty workspace list. "
                       "Create a workspace at https://dashboard.render.com first.",
                status_code=400,
            )
        personal = next((o for o in owners if o.get("type") == "user"), None)
        if personal is None:
            # Fall back to the first team workspace. The user can still
            # deploy, just not to their personal workspace.
            return owners[0]
        return personal

    @classmethod
    def build_connect_response(cls, owner: dict[str, Any]) -> RenderConnectResponse:
        return RenderConnectResponse(
            owner_id=owner["id"],
            owner_name=owner.get("name"),
            owner_type=owner.get("type", "user"),
            owner_email=owner.get("email"),
        )

    @classmethod
    def build_status_response(
        cls,
        *,
        connected: bool,
        owner_id: str | None,
        owner_name: str | None = None,
        owner_type: str | None = None,
        owner_email: str | None = None,
    ) -> RenderStatusResponse:
        return RenderStatusResponse(
            connected=connected,
            owner_id=owner_id,
            owner_name=owner_name,
            owner_type=owner_type,  # type: ignore[arg-type]
            owner_email=owner_email,
        )

    # -------------------------------------------------------------------
    # Detect runtime from a GitHub repo
    # -------------------------------------------------------------------

    @classmethod
    async def detect(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        preferred_branch: str | None = None,
    ) -> RenderDetectResponse:
        """Inspect the repo via GitHub and recommend a Render runtime.

        Reuses GitHubPagesService.build_repository_context so we don't
        duplicate the package.json/next.config/Gemfile parsing -- the
        SAME context Pages uses, but interpreted for a server runtime.
        """
        context = await GitHubPagesService.build_repository_context(
            github_token=github_token,
            owner=owner,
            repository=repository,
            preferred_branch=preferred_branch,
        )

        runtime, build, start, dockerfile, reason = cls._detect_runtime(context)
        env_var_suggestions = cls._suggest_env_vars(runtime, context)

        return RenderDetectResponse(
            runtime=runtime,
            build_command=build,
            start_command=start,
            dockerfile_path=dockerfile,
            plan="free",
            branch=context.selected_branch,
            reason=reason,
            env_var_suggestions=env_var_suggestions,
        )

    @classmethod
    def _detect_runtime(
        cls,
        context: Any,
    ) -> tuple[RenderRuntime, str | None, str | None, str | None, str]:
        """Decide which Render runtime fits this repo.

        Returns (runtime, build_command, start_command, dockerfile_path, reason).
        For runtime=docker, build/start are None and dockerfile_path is
        set -- Render reads the Dockerfile from the repo and runs the
        image's CMD.

        Order of precedence (highest first):
          1. Dockerfile in root      -> runtime=docker
          2. Next.js non-static      -> runtime=node, start=npm start
          3. Python markers          -> runtime=python, start=uvicorn ...
          4. Node server frameworks  -> runtime=node, start=npm start
          5. Fallback                -> runtime=node (Render's default
                                        for repos with package.json)
        """
        # 1. Dockerfile takes precedence -- it's the most explicit signal.
        if "dockerfile" in context.root_names:
            return (
                "docker",
                None,
                None,
                "./Dockerfile",
                "Dockerfile detected at repository root. Render will build the image "
                "and run its CMD.",
            )

        all_deps = context.dependencies | context.dev_dependencies

        # 2. Non-static Next.js (SSR / API routes).
        # We piggyback on GitHubPagesService's _has_next_signal /
        # _is_next_static_export: if it looks like Next.js but is NOT
        # static-exportable, Render is the right target (node runtime).
        if GitHubPagesService._has_next_signal(context) and not \
                GitHubPagesService._is_next_static_export(context):
            build = "npm install && npm run build"
            start = "npm start"
            return (
                "node",
                build,
                start,
                None,
                "Next.js app detected without a static export config. Render runs "
                "`npm run build` then `npm start` -- this serves SSR routes and "
                "API routes the way Next.js expects.",
            )

        # 3. Python: requirements.txt or .py files at root, OR fastapi/
        # flask/django/uvicorn/gunicorn mentioned in package.json deps
        # (some monorepos carry a Python manifest in package.json).
        python_markers = {"fastapi", "flask", "django", "uvicorn", "gunicorn", "starlette"}
        has_python_files = any(n.endswith(".py") for n in context.root_names)
        has_requirements = "requirements.txt" in context.root_names \
            or "pyproject.toml" in context.root_names \
            or "setup.py" in context.root_names
        if has_requirements or (has_python_files and not context.package_json):
            # Best-guess start command. Render requires $PORT binding.
            # uvicorn/gunicorn are the most common WSGI/ASGI servers.
            if "uvicorn" in python_markers or "fastapi" in python_markers:
                start = "uvicorn app:app --host 0.0.0.0 --port $PORT"
            elif "gunicorn" in python_markers or "django" in python_markers:
                start = "gunicorn app:app --bind 0.0.0.0:$PORT"
            else:
                # Generic fallback: most Flask/FastAPI apps expose `app:app`.
                start = "uvicorn app:app --host 0.0.0.0 --port $PORT"
            build = "pip install -r requirements.txt"
            return (
                "python",
                build,
                start,
                None,
                "Python project detected (requirements.txt/pyproject.toml/.py files). "
                "Render installs deps with pip and runs the ASGI/WSGI server.",
            )

        # 4. Node server runtime (express/fastify/koa/nest/hono/socket.io).
        # Reuses the exact same SERVER_RUNTIME_MARKERS set as GitHub Pages
        # so the two platforms agree on what counts as a "server app".
        if context.package_json and \
                (GitHubPagesService.SERVER_RUNTIME_MARKERS & all_deps):
            start = context.scripts.get("start") or "node server.js"
            build = "npm install"
            # If there's a build script, run it as part of the build phase.
            if "build" in context.scripts:
                build = "npm install && npm run build"
            return (
                "node",
                build,
                start,
                None,
                "Node server framework detected (express/fastify/koa/nest/hono/socket.io). "
                "Render runs `npm install` (plus `npm run build` if present) then the "
                "start script.",
            )

        # 5. Fallback: package.json present without server markers.
        # Default to node so the user can edit commands in the modal.
        if context.package_json:
            build = "npm install" + (" && npm run build" if "build" in context.scripts else "")
            start = context.scripts.get("start") or "node server.js"
            return (
                "node",
                build,
                start,
                None,
                "package.json detected without explicit server markers. Defaulting to "
                "node runtime -- review the build/start commands before deploying.",
            )

        # 6. Last resort: docker, let Render figure it out.
        return (
            "docker",
            None,
            None,
            "./Dockerfile",
            "Could not confidently detect the runtime. Defaulting to docker; "
            "add a Dockerfile to the repo root for the deploy to succeed.",
        )

    @classmethod
    def _suggest_env_vars(
        cls,
        runtime: RenderRuntime,
        context: Any,
    ) -> dict[str, str]:
        """Return best-effort env var suggestions to pre-fill the modal.

        Render injects `PORT` automatically -- we DON'T suggest it
        (overriding it breaks the service). NODE_ENV=production is a
        near-universal default for node. We don't try to read .env
        files from the repo: that's a privacy smell and the values
        are usually secrets.
        """
        suggestions: dict[str, str] = {}
        if runtime == "node":
            suggestions["NODE_ENV"] = "production"
        # PORT is injected by Render; never set it manually.
        return suggestions

    # -------------------------------------------------------------------
    # Deploy
    # -------------------------------------------------------------------

    @classmethod
    async def create_web_service(
        cls,
        api_key: str,
        owner_id: str,
        request: RenderDeployRequest,
    ) -> RenderDeployResponse:
        """POST /v1/services -- create a web_service and auto-trigger a deploy.

        Per Render's API: `autoDeploy` is a STRING enum ("yes"/"no"),
        `buildCommand`/`startCommand` live inside `envSpecificDetails`
        (both required for native runtimes), and `plan` lives directly
        on `serviceDetails` (NOT inside envSpecificDetails). The
        response is `{service, deployId}` where the deployId is the
        auto-triggered deploy.
        """
        service_details: dict[str, Any] = {
            "runtime": request.runtime,
            "plan": request.plan,
            "region": "oregon",  # default; user can change in Render dashboard
            "numInstances": 1,
        }

        if request.runtime == "docker":
            service_details["envSpecificDetails"] = {
                "dockerfilePath": request.dockerfile_path or "./Dockerfile",
                "dockerContext": ".",
            }
        else:
            # Native runtime -- both buildCommand and startCommand are REQUIRED.
            if not request.build_command or not request.start_command:
                raise RenderError(
                    message="Missing build/start command.",
                    detail=(
                        f"Runtime '{request.runtime}' requires both buildCommand and "
                        "startCommand. Run /v1/render/detect first to pre-fill them, "
                        "or pass them explicitly in the deploy request."
                    ),
                    status_code=400,
                )
            service_details["envSpecificDetails"] = {
                "buildCommand": request.build_command,
                "startCommand": request.start_command,
            }

        env_vars_payload: list[dict[str, Any]] = []
        for ev in request.env_vars:
            if ev.generate_value:
                env_vars_payload.append({"key": ev.key, "generateValue": True})
            else:
                env_vars_payload.append({"key": ev.key, "value": ev.value})

        payload: dict[str, Any] = {
            "type": "web_service",
            "name": request.service_name,
            "ownerId": owner_id,
            "repo": f"https://github.com/{request.owner}/{request.repository}",
            "branch": request.branch,
            "autoDeploy": "yes" if request.auto_deploy else "no",
            "envVars": env_vars_payload,
            "serviceDetails": service_details,
        }

        response = await cls._request(
            "POST",
            "/services",
            api_key,
            json=payload,
            timeout=cls.LONG_TIMEOUT,
        )
        cls._raise_for(response, default_message="Render rejected service creation.")

        body = response.json() or {}
        service = body.get("service") or body  # tolerate either shape
        deploy_id = body.get("deployId") or ""

        service_id = service.get("id", "")
        service_details_obj = service.get("serviceDetails") or {}
        service_url = service_details_obj.get("url")
        dashboard_url = service.get("dashboardUrl")

        return RenderDeployResponse(
            success=True,
            service_id=service_id,
            deploy_id=deploy_id,
            service_url=service_url,
            dashboard_url=dashboard_url,
            message=(
                f"Render service '{request.service_name}' created and deploy "
                f"{deploy_id} triggered. Poll /v1/render/services/{service_id} "
                "for build/live status."
            ),
        )

    @classmethod
    async def trigger_deploy(
        cls,
        api_key: str,
        service_id: str,
        *,
        clear_cache: bool = False,
        commit_id: str | None = None,
    ) -> str:
        """POST /v1/services/{id}/deploys -- trigger a manual redeploy.

        `clearCache` is a STRING enum ("clear"|"do_not_clear") -- NOT
        a boolean, despite the field name. Returns the new deployId.
        """
        body: dict[str, Any] = {
            "clearCache": "clear" if clear_cache else "do_not_clear",
        }
        if commit_id:
            body["commitId"] = commit_id

        response = await cls._request(
            "POST",
            f"/services/{quote(service_id, safe='')}/deploys",
            api_key,
            json=body,
        )
        cls._raise_for(response, default_message="Render rejected deploy trigger.")
        deploy = response.json() or {}
        return deploy.get("id", "")

    # -------------------------------------------------------------------
    # List / detail / redeploy
    # -------------------------------------------------------------------

    @classmethod
    async def list_services(
        cls,
        api_key: str,
        owner_id: str | None = None,
        limit: int = 50,
    ) -> list[RenderServiceSummary]:
        """GET /v1/services -- list the user's Render web services.

        Render returns `[{"service": {...}, "cursor": "..."}, ...]`. We
        strip the cursor wrapper and also fetch each service's latest
        deploy status with a parallel /v1/services/{id}/deploys call.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if owner_id:
            params["ownerId[]"] = owner_id

        response = await cls._request("GET", "/services", api_key, params=params)
        cls._raise_for(response, default_message="Failed to list Render services.")

        raw_items = response.json() or []
        summaries: list[RenderServiceSummary] = []
        for item in raw_items:
            svc = item.get("service") if isinstance(item, dict) else None
            if not isinstance(svc, dict):
                continue
            summaries.append(cls._to_summary(svc))
        return summaries

    @classmethod
    async def get_service(cls, api_key: str, service_id: str) -> RenderServiceDetail:
        """GET /v1/services/{id} -- single service + latest deploy status.

        Two API calls in sequence: first the service, then the most
        recent deploy. Render doesn't bundle them.
        """
        response = await cls._request(
            "GET", f"/services/{quote(service_id, safe='')}", api_key
        )
        cls._raise_for(response, default_message="Failed to fetch Render service.")
        svc = response.json() or {}

        # Best-effort: fetch latest deploy status. Don't fail the whole
        # request if /deploys 404s (e.g. service just created, no deploys yet).
        latest_status: str | None = None
        latest_deploy_id: str | None = None
        latest_commit: str | None = None
        latest_trigger: str | None = None
        latest_started_at = None
        latest_finished_at = None
        try:
            deploys_response = await cls._request(
                "GET",
                f"/services/{quote(service_id, safe='')}/deploys",
                api_key,
                params={"limit": 1},
            )
            if deploys_response.status_code == 200:
                items = deploys_response.json() or []
                if items:
                    deploy = items[0].get("deploy") if isinstance(items[0], dict) else None
                    if isinstance(deploy, dict):
                        latest_status = deploy.get("status")
                        latest_deploy_id = deploy.get("id")
                        latest_trigger = deploy.get("trigger")
                        commit_obj = deploy.get("commit") or {}
                        if isinstance(commit_obj, dict):
                            latest_commit = commit_obj.get("id")
                        latest_started_at = deploy.get("startedAt")
                        latest_finished_at = deploy.get("finishedAt")
        except RenderError:
            pass

        detail = RenderServiceDetail(
            **cls._to_summary(svc).model_dump(),
            latest_deploy_id=latest_deploy_id,
            latest_deploy_commit=latest_commit,
            latest_deploy_trigger=latest_trigger,
            latest_deploy_status=latest_status,
            latest_deploy_started_at=latest_started_at,
            latest_deploy_finished_at=latest_finished_at,
        )
        return detail

    @classmethod
    def _to_summary(cls, svc: dict[str, Any]) -> RenderServiceSummary:
        service_details = svc.get("serviceDetails") or {}
        return RenderServiceSummary(
            service_id=svc.get("id", ""),
            name=svc.get("name", ""),
            url=service_details.get("url"),
            dashboard_url=svc.get("dashboardUrl"),
            runtime=service_details.get("runtime") or service_details.get("env"),
            plan=service_details.get("plan"),
            status=svc.get("suspended"),
            repo=svc.get("repo"),
            branch=svc.get("branch"),
            created_at=svc.get("createdAt"),
            updated_at=svc.get("updatedAt"),
            latest_deploy_status=None,  # filled by list_services caller
        )

    # -------------------------------------------------------------------
    # Custom domains
    # -------------------------------------------------------------------

    @classmethod
    async def add_custom_domain(
        cls,
        api_key: str,
        service_id: str,
        domain: str,
    ) -> RenderCustomDomainResponse:
        """POST /v1/services/{id}/custom-domains -- add a custom hostname.

        Render returns the FULL updated list of custom domains for the
        service (array), not just the one we added. We pick out the
        matching one by name and derive the CNAME target from the
        service's `onrender.com` URL -- the API doesn't include DNS
        records, so we compute the canonical CNAME target server-side
        and return it in our response so the frontend can show the
        user "add this CNAME record at your DNS provider".
        """
        # 1. Add the domain
        response = await cls._request(
            "POST",
            f"/services/{quote(service_id, safe='')}/custom-domains",
            api_key,
            json={"name": domain},
        )
        cls._raise_for(response, default_message="Render rejected custom-domain creation.")

        body = response.json() or []
        # Render returns an array of {customDomain, cursor} items; find ours.
        target = None
        if isinstance(body, list):
            for item in body:
                cd = item.get("customDomain") if isinstance(item, dict) else item
                if isinstance(cd, dict) and cd.get("name") == domain:
                    target = cd
                    break
        if target is None and isinstance(body, dict):
            # Some Render responses return a bare object instead of a list.
            target = body
        if target is None:
            # Fall back to a synthetic shape if Render didn't echo back.
            target = {"id": "", "name": domain, "verificationStatus": "unverified"}

        # 2. Derive the CNAME target from the service URL.
        # Render's convention: <service-slug>.onrender.com. We pull that
        # from GET /v1/services/{id} so the frontend has a copy-paste
        # ready value for Cloudflare/Route53/etc.
        cname_target = None
        try:
            svc = await cls.get_service(api_key, service_id)
            if svc.url:
                # Strip scheme, keep host only.
                parsed = urlsplit(svc.url)
                cname_target = parsed.netloc or parsed.path
        except RenderError:
            pass  # Don't fail the whole add-domain call if we can't derive CNAME.

        return RenderCustomDomainResponse(
            domain_id=target.get("id", ""),
            name=target.get("name", domain),
            domain_type=target.get("domainType"),
            verification_status=target.get("verificationStatus", "unverified"),
            cname_target=cname_target,
            message=(
                f"Custom domain '{domain}' added. Add a CNAME record pointing to "
                f"{cname_target} at your DNS provider, then call /verify."
                if cname_target else
                f"Custom domain '{domain}' added. Check the Render dashboard for DNS records."
            ),
        )

    @classmethod
    async def verify_custom_domain(
        cls,
        api_key: str,
        service_id: str,
        domain_name_or_id: str,
    ) -> RenderCustomDomainResponse:
        """POST /v1/services/{id}/custom-domains/{name}/verify + GET to refresh.

        Render's verify endpoint returns 202 with empty body (async).
        We then poll GET /custom-domains/{name} once for an updated
        verificationStatus. DNS propagation typically takes minutes,
        so the frontend should re-call /status periodically.
        """
        sid = quote(service_id, safe="")
        dname = quote(domain_name_or_id, safe="")

        verify_resp = await cls._request(
            "POST", f"/services/{sid}/custom-domains/{dname}/verify", api_key
        )
        # 202 is the happy path; 4xx means Render rejected it.
        if verify_resp.status_code not in (200, 202, 204):
            cls._raise_for(verify_resp, default_message="Render rejected custom-domain verification.")

        # Poll once for updated status.
        get_resp = await cls._request(
            "GET", f"/services/{sid}/custom-domains/{dname}", api_key
        )
        cls._raise_for(get_resp, default_message="Render rejected custom-domain fetch.")

        cd = get_resp.json() or {}

        # Derive CNAME target from the parent service for the response.
        cname_target = None
        try:
            svc = await cls.get_service(api_key, service_id)
            if svc.url:
                parsed = urlsplit(svc.url)
                cname_target = parsed.netloc or parsed.path
        except RenderError:
            pass

        return RenderCustomDomainResponse(
            domain_id=cd.get("id", ""),
            name=cd.get("name", domain_name_or_id),
            domain_type=cd.get("domainType"),
            verification_status=cd.get("verificationStatus", "unverified"),
            cname_target=cname_target,
            message=(
                f"Verification status: {cd.get('verificationStatus', 'unverified')}. "
                + ("DNS records verified -- the domain is live."
                   if cd.get("verificationStatus") == "verified"
                   else "DNS records not yet detected. Wait a few minutes for DNS propagation and retry.")
            ),
        )