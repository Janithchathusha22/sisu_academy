# Frontend without a backend

From this frontend directory, run `npm ci` then `npm run build:static`.
Publish only the generated `dist` directory, never the source directory.
Use `npm run preview:static` to review the production output locally.

This build opens the platform preview automatically on any host. Choose a
fictional account on the login screen, then click Open my workspace. Sample
credentials are shown on that screen. Workspace data is browser/session-local;
real authentication, payments, email, server uploads and live services are not
provided by this static preview.

## Netlify

Commit and push the changes, including the repository-root `netlify.toml`.
Base directory: `_SISU/institute_lms/frontend`; build command:
`npm run build:netlify`; publish directory: `dist`.
Alternatively, upload the generated `dist` folder through Netlify manual deploy.

## GitHub Pages

Publish the contents of `dist` as the Pages artifact, not the source folder.
The static build uses relative asset paths to support repository subpaths.
The preview uses hash navigation, so a SPA fallback is not required.

The existing `npm run build` command remains the server-connected Frappe build.
