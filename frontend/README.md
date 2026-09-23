# DeployBridge Frontend

The frontend for DeployBridge is built focusing on a fast, lightweight, and cinematic user experience without relying on heavy JavaScript frameworks like React or Vue. 

## Current Scope & Architecture

The application is served as static files (`.html`, `.js`, `.css`) and relies on vanilla JavaScript for logic and TailwindCSS (via CDN) for styling.

### Key Technologies
- **HTML/CSS**: Vanilla HTML5 with TailwindCSS loaded via CDN for rapid utility-based styling.
- **JavaScript**: Pure Vanilla JS, heavily modularized into specific files per feature.
- **Animations & Scrolling**: 
  - [GSAP](https://gsap.com/) & ScrollTrigger for complex timeline animations.
  - [Lenis](https://lenis.darkroom.engineering/) for smooth scrolling.
- **Theming**: Custom CSS variables for theming with built-in dark/light mode toggle support.

### Directory Structure
- `index.html`: The main landing page, containing the cinematic intro, ecosystem showcase, and hero sections.
- `docs.html`: Frontend documentation and guide pages.
- `templates/`: Contains other HTML views (e.g., `auth.html`).
- `js/`: Modular JavaScript files handling specific domain logic:
  - `agent.js`: Logic for the AI deployment agent interactions.
  - `app-shell.js`: Global UI and layout handling.
  - `auth.js`: Authentication state and UI logic.
  - `deployments.js`: Managing deployment listings and triggers.
  - `overview.js`: Dashboard overview logic.
  - `profile.js`: User profile management.
  - `reports.js`: Rendering and managing AI analysis reports.
  - `repositories.js`: GitHub repository listing and selection.
  - `settings.js`: User settings and configurations.
- `static/`: Contains static assets like images, icons, or custom CSS files.

## Running the Frontend

Because the frontend consists of static files, it can be served using any basic HTTP server.

For example, using Python's built-in server:
```bash
cd frontend
python -m http.server 3000
```
Then navigate to `http://localhost:3000` in your browser.

## Styling Approach
The UI heavily utilizes glassmorphism, background gradients, and CSS mask composite techniques to create a premium, modern feel. The Tailwind configuration is injected directly into the HTML `<head>`, extending custom fonts (Ubuntu, JetBrains Mono, Montenegrin Gothic One) and color variables linked to the `data-theme` attribute.
