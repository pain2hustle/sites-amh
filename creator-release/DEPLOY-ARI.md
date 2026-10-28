# Ari-only GitHub Actions deployment

Prepared for `pain2hustle/sites-amh`, main. This proposal is not a successful deployment and does not establish that the required Cloudflare project exists.

## Files to add after review

- `deploy-ari.yml` → `.github/workflows/deploy-ari.yml`
- `verify_ari_pages_project.py` → `tools/verify_ari_pages_project.py`
- This documentation → `creator-release/DEPLOY-ARI.md`

The workflow is manual-only (`workflow_dispatch`), restricts execution to this repository's main branch, checks out the selected commit, and builds only the reviewed 55-file Ari standalone artifact. It does not modify the existing `sites-amh` Pages project's build command, branch controls, domains or deployments. It does not upload private source/QA evidence. Four verified videos remain below the requested minimum of sixteen.

## Secure setup

The single required repository Actions secret is `CLOUDFLARE_API_TOKEN`. The user enters and saves it directly at GitHub's encrypted repository-secret form; do not put it in chat, source, command arguments, logs, artifacts or screenshots. The account identifier is not a credential and is pinned in the workflow and verifier: `a08783a0d3715df907ed5ccad38f0dcf`, the supplied Artificialmindhive account also seen in the existing deployment links. No second account-ID secret is necessary.

Recommended Cloudflare token permission: **Account → Cloudflare Pages → Edit**, limited to that specific account. Do not use a Global API Key or broad all-account permissions. Pages Edit is account-wide Pages capability, not a hard project-specific token boundary; the fixed project guards limit this workflow, while repository collaborators able to change workflows could use the stored token. Review collaborator access and rotate/revoke the token when appropriate. No credential is created by this workflow.

Actions uses `contents: read` only. Official GitHub checkout/setup-node and official Cloudflare wrangler-action are pinned to verified commit SHAs; Wrangler is pinned to 4.136.3. No `deployments: write`, PAT, OIDC, domain/DNS, billing or permission changes are required. Credentials are exposed only to project verification and the deploy action, not to the site build.

## First project and execution

The verifier first checks the known existing **sites-amh.pages.dev** project in the pinned account using the documented API. It then reads **ari1of1**. If absent (HTTP 404), it makes one explicitly authorized create request with only name **ari1of1** and production branch **main**. Before uploading, both existing and newly created results must match exactly **ari1of1.pages.dev** and **main**. Redirects, collisions, unexpected hostnames, authentication failures and malformed responses fail closed. It never accepts a suffix, deletes a project, retries an uncertain creation, disables Git integration or changes existing settings. A timed-out creation is reported as uncertain; a later run checks existing state before any new create attempt. If Cloudflare allocates an unexpected hostname, no content is uploaded and the discrepancy must be reported, not silently used. Exact availability is not assumed before API confirmation.

After the workflow is on the default branch, GitHub → Actions → **Deploy Ari (manual)** → Run workflow on **main**. A successful upload is not complete browser QA: verify the exact live hostname, eight routes, images, exact tracked shop links, mobile/desktop rendering and official video playback/fallbacks. Keep the existing shared-host Ari URL working until that verification is complete.

The repository had no `.github/workflows` files and no Actions runs at inspection (2026-10-28). The signed-in browser showed **Get started with GitHub Actions** and workflow configuration controls, not a disabled notice. Actions settings were subsequently verified read-only: Allow all actions and reusable workflows is selected; default GITHUB_TOKEN permissions are read-only; fork PRs require first-time contributor approval. No settings were changed. Actual hosted-runner scheduling and Cloudflare credential validity remain unproven until the first dispatch.

## Existing failure diagnostics

The unrelated shared-host release `e6988172fd65ad4172d0f0d357bf8e8b7d576e4b` failed Cloudflare deployment `ef558454-a8b9-48e6-8944-c211fb8c857c`; the same complete build passed locally. The cause remains unknown until its detailed log is read. Pages Read or Pages Write is accepted by the documented deployment-log endpoint. This deployment workflow intentionally does not fetch, upload or publish those private logs and does not blindly retry the failed shared-site release.

## Official references

- Cloudflare CI and minimal token setup: https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/
- Project creation API: https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/create/
- Project identity API: https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/get/
- Deployment logs API: https://developers.cloudflare.com/api/resources/pages/subresources/projects/subresources/deployments/subresources/history/subresources/logs/methods/get/
- Manual dispatch/default-branch requirement: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
- Official deploy action: https://github.com/cloudflare/wrangler-action/tree/953926a2e2182532811c01a25e53647d93bf07c0
