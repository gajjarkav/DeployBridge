# GitHub Pages Framework Support

## Purpose

This document describes how DeployBridge detects, selects, and deploys GitHub Pages-compatible static sites across multiple repository types.

## GitHub Pages Support Model

GitHub Pages can publish a site either from a branch-based source or from a custom GitHub Actions workflow. DeployBridge uses the custom workflow model because it supports both plain static repositories and repositories that need a build step before publishing.

DeployBridge writes a workflow file into the target repository, enables GitHub Pages with `build_type=workflow`, and triggers the workflow through `workflow_dispatch`.

## Supported Profiles

| Profile | Repository Type | Detection Signals | Build Logic | Publish Path | Workflow |
| --- | --- | --- | --- | --- | --- |
| `html` | Plain static HTML/CSS/JS | `index.html`, other `.html/.css/.js` files, static asset folders, no framework package setup | No build | repository root | `html.yml` |
| `jekyll` | Jekyll site | `_config.yml`, `_posts`, Gemfile with `jekyll` or `github-pages` | Jekyll build action | `_site` | `jekyll.yml` |
| `node-static` | React, Vite, Vue, Astro, Gatsby, Angular static, Nuxt static, and similar Node static builds | `package.json`, framework dependencies, `build` or `generate` scripts | install + build/generate | resolved artifact dir | `node-static.yml` |
| `next-static` | Next.js static export only | Next.js dependency or config plus static export signal | install + build/export | `out` | `next-static.yml` |

## Detection Rules

### `html`

DeployBridge selects `html` when:

- no framework package setup is detected
- no Jekyll or Next.js signals are found
- the repository contains common static files such as `.html`, `.css`, `.js`
- or the root contains static asset folders such as `assets`, `static`, `css`, or `js`

### `jekyll`

DeployBridge selects `jekyll` when one of these is present:

- `_config.yml`
- `_posts`
- `Gemfile` containing `jekyll`
- `Gemfile` containing `github-pages`

### `node-static`

DeployBridge selects `node-static` when:

- `package.json` exists
- and framework markers such as `react`, `vite`, `vue`, `astro`, `gatsby`, `@angular/core`, or `nuxt` are present
- or a `build` or `generate` script exists in `package.json`
- and the repository does not look like a server-first runtime

### `next-static`

DeployBridge selects `next-static` only when:

- the repository has Next.js signals such as a `next` dependency or `next.config.*`
- and the repository also shows static export compatibility through:
  - `output: 'export'` in the Next config, or
  - a script that runs `next export`

If a Next.js repository does not satisfy those static-export checks, DeployBridge rejects it as unsupported for GitHub Pages in Phase 4.

## Node Static Build Logic

The `node-static` profile uses this workflow logic:

1. Install dependencies with `npm ci` when `package-lock.json` exists.
2. Fall back to `npm install` when no lockfile exists.
3. Run `npm run generate` when that script exists.
4. Otherwise run `npm run build`.
5. Resolve the artifact directory in this order:
   - `dist`
   - `build`
   - `out`
   - `public`
   - `.output/public`
   - `dist/<package-name>/browser`

If none of those output directories exists after the build, the workflow fails with a clear message.

## Next.js Static Export Logic

The `next-static` profile uses this workflow logic:

1. Install dependencies with `npm ci` when `package-lock.json` exists.
2. Fall back to `npm install` when no lockfile exists.
3. Run `npm run build`.
4. Run `npm run export` when an export script exists.
5. Verify that `out` exists before uploading.

If `out` does not exist, the workflow fails and instructs the repository owner to configure static export correctly.

## Frontend Deploy Logic

The dashboard deployment flow uses this sequence:

1. User clicks the GitHub Pages button.
2. Frontend calls the detection API.
3. Frontend shows the detected profile and the detection reason.
4. User may keep `auto` or manually override with one of the supported profiles.
5. Frontend sends the final deploy request.
6. Backend resolves the final profile, writes the matching workflow, enables Pages, removes stale DeployBridge workflow files, and triggers the workflow.

## API Surface

### Detect

`POST /v1/github-pages/detect`

Request:

```json
{
  "owner": "username",
  "repository": "repo-name"
}
```

Response:

```json
{
  "detected_profile": "node-static",
  "supported_profiles": ["auto", "html", "jekyll", "node-static", "next-static"],
  "reason": "Detected a Node-based static site project that can be built before publishing."
}
```

### Deploy

`POST /v1/github-pages/deploy`

Request:

```json
{
  "owner": "username",
  "repository": "repo-name",
  "deployment_profile": "auto"
}
```

Response:

```json
{
  "success": true,
  "message": "GitHub Pages deployment started for \"repo-name\" using the \"node-static\" profile on \"main\".",
  "resolved_profile": "node-static",
  "workflow_template": "node-static.yml"
}
```

## Non-Goals For Phase 4

Phase 4 does not support:

- SSR deployments
- API/server runtimes
- non-static Next.js repositories
- non-static Nuxt or SvelteKit server modes
- package managers beyond npm
- arbitrary server-side framework deployment

## Workflow Inventory

- `html.yml`: upload repository root directly
- `jekyll.yml`: run Jekyll build and upload `_site`
- `node-static.yml`: install, build/generate, resolve output folder, upload output
- `next-static.yml`: install, build/export, upload `out`

## References

- GitHub Pages custom workflow publishing:
  https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub Pages publishing source guidance:
  https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
