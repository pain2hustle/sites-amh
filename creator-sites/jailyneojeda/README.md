# Jailyne Ojeda — first named-host release

Target: **https://jailyneojeda.pages.dev**, exact Pages project **jailyneojeda**.
This is a prepared deployment source, not proof of availability or a live site.

## Contents
The `site/` folder is a buildless plain-file export: 143 files, 56 HTML routes, 33 verified videos (24 YouTube / 9 Instagram), 17 official products and eight verified social profiles. `manifest.json` records every byte size and SHA-256. Source URLs and product price/date evidence are in `SOURCES.md`. No binary release archive needs unpacking in CI; images and fonts remain normal individually reviewable files.

## Separate manual deployment
The optional `.github/workflows/deploy-jailyne.yml` is manual-only and requires separately verified authentication. Publishing these source files does not dispatch it. The same validated output can be deployed through the separately authorized Cloudflare operations route; use only the exact account and project, and verify existing project ownership before any upload.

The workflow is `workflow_dispatch` only, fixed to **pain2hustle/sites-amh**, **main**, a separate **jailyneojeda-production** concurrency group, the pinned Artificialmindhive account, and the exact destination. It stages only this creator's bytes, never the shared business build. Existing `build.py`, packs, shared directory, Ari workflow/guard and deployments are not changed. Use a `[CF-Pages-Skip]` commit prefix for the separately authorized repository publication, preserving the existing shared-host skip convention.

`tools/stage_jailyne_site.py` pins this manifest, validates every path/count/size/hash, refuses symlinks/extra files/functions, copies into its own temporary directory and atomically installs `_jailyne_site` only if no output exists. It uses Python's standard library, no site generators or network. Do not replace it with a broad copy, unpacking command, or unrelated build.

`tools/verify_jailyne_pages_project.py` uses the encrypted repository Actions secret only in the CI verifier. It first reads the known `sites-amh.pages.dev` project in the pinned account. It reads `jailyneojeda`; only HTTP404 permits one exact-name create. It requires the exact returned name, `jailyneojeda.pages.dev`, and production branch `main`. No suffix, domain purchase/DNS, permission change, redirect following, deletion, credential printing or retry is allowed. Timeouts are uncertain, not success; inspect the exact project before any later attempt.

**First-release overwrite protection:** an existing deployed project, Git-integrated project, or custom-domain configuration stops the upload for ownership/content review. A pre-existing empty, matching, direct-upload project may be used. This intentionally stops subsequent releases after first publication until an authorized update policy tied to the known deployment is reviewed. It does not silently overwrite an exact-name site or Jailyne's original website.

## Credential boundary
The existing repository secret is `CLOUDFLARE_API_TOKEN`; its value must never be put in source, chat, command arguments, screenshots or output. Agents do not read it. Cloudflare Pages Edit remains an account-wide capability, not project-scoped access; the fixed workflow guard is not a token permission boundary. No new token creation, grant, settings edit or collaborator change is part of this proposal.

Official GitHub checkout/setup-node and Cloudflare wrangler-action are commit-pinned to the already-reviewed Ari route; Wrangler is pinned to 4.136.3. `GITHUB_TOKEN` permissions are only `contents: read`, and checkout does not retain credentials. The staging step receives no Cloudflare secret. There are no push/PR triggers and no automatic deployment on adding these files.

## Quality status and release gate
Static checks passed for all 56 routes, 42 raster assets, eight socials, 17 product links/prices and 33 distinct media IDs. Core interaction mocks: 37 assertions; extra UI mocks:24; fresh per-click18+ gate:12 groups. Separate deployment offline checks:43; staging checks:29. No network or real credential was used by these deployment tests.

Actual whole-page browser responsive QA and live playback remain release checks, not established by the offline tests. After authorized first publication, inspect the exact public host at320/390/768/1440 widths, both themes, cinematic Skip, hamburger/dock, filters, gallery, share/watchlist, video close/reopen/background cleanup, product detail links, and the age-prompt's Cancel/Escape/backdrop. Do not affirm age during testing. Verify original-platform fallbacks if embeds are blocked; a loaded iframe is not proof of playback. Reconfirm product prices if release is delayed.

## Primary implementation references
- [Cloudflare direct upload CI](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/)
- [Project lookup](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/get/)
- [Project creation](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/create/)
- [GitHub manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
