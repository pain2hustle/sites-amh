# Read-only Cloudflare authentication diagnostic

This separate manual workflow makes **one GET**, to the exact existing `sites-amh` Pages project in account `a08783a0d3715df907ed5ccad38f0dcf`. It cannot create a project, upload a website, deploy, retry, change credentials, broaden permissions or follow redirects. It does not invoke the existing deployment helper. Its only GitHub permission is `contents: read`.

The secret remains in GitHub Actions. Like the existing verifier, the diagnostic removes leading/trailing whitespace and supplies the documented `Authorization: Bearer` header. The public logs contain only fixed outcome labels, bounded numeric HTTP/Cloudflare error codes and a hard-coded category for known codes. API message strings, headers, response bodies, IDs, token values, token length/prefix and exception text are never printed or saved. Unknown error categories remain unclassified rather than guessed.

The first deployment run reached the known-project GET and returned HTTP401. Its response body was intentionally withheld, so that result does not establish that the pasted credential itself is wrong. The published environment-variable name, fixed account, API endpoint, HTTP method and Bearer construction match official documentation. A leading/trailing space was already removed before that failing request.

This diagnostic does not use a token-verify endpoint because token ownership is not yet known. Cloudflare documents `/user/tokens/verify` for user tokens and `/accounts/{account_id}/tokens/verify` for account-owned tokens. Failure at the wrong endpoint must not be interpreted as an invalid token. Pages supports account-owned tokens. Token verification also does not enforce client-IP filtering; an active status alone would not prove that a GitHub runner can access Pages in the intended account.

Run only after review, on the default main branch. A successful read-only diagnostic is not a deployment and must not be described as a live named host. Interpret the safe result before deciding the next action; do not repeatedly rerun an unchanged rejection.

## Official references

- Pages GET, Bearer authentication, accepted Pages Read/Write permissions: https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/get/
- Account token compatibility (Pages supported): https://developers.cloudflare.com/fundamentals/api/get-started/account-owned-tokens/
- User token verification: https://developers.cloudflare.com/api/resources/user/subresources/tokens/methods/verify/
- Account token verification: https://developers.cloudflare.com/api/resources/accounts/subresources/tokens/methods/verify/
- IP/TTL restrictions and verification caveat: https://developers.cloudflare.com/fundamentals/api/how-to/restrict-tokens/
- Official SDK authentication categories 9106/10000: https://github.com/cloudflare/workers-sdk/blob/main/packages/wrangler/src/core/handle-errors.ts
- Official Cloudflare API integration discussion of 9109/10000 ambiguity: https://github.com/cloudflare/mcp/blob/main/AGENTS.md
