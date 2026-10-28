# Eleven independent creator sources

This is an additive, partial source delivery—not a public creator directory and not a deployment of the repository root. Existing pages, Ari, Jailyne, workflows, and root entrypoints are preserved.

| Creator | Standalone source root |
|---|---|
| NICHA | `creator-sites/immapeaches/site` |
| Anna Cowgirlbgo | `creator-sites/annacowgirlbgo/site` |
| The Crooked Man | `creator-sites/thecrookedman10/site` |
| Pamela Yanez | `creator-sites/pamela-yanez/site` |
| Adina Y Flores | `creator-sites/adina-y-flores/site` |
| Danny Alvarez | `creator-sites/dannyalvarez57/site` |
| Kat · Costco Ho | `creator-sites/allcapskat/site` |
| Ashley Tienda | `creator-sites/ashleytienda/site` |
| Isabella | `creator-sites/isatobaa/site` |
| Gracie Bon | `creator-sites/graciebon/site` |
| Sherry Foreign | `creator-sites/sherryforeign/site` |

Each source directory must be served at its own origin root. Root-relative URLs are deliberate; no nested URL-prefix compatibility or registered domain is claimed.

## Stage one creator without deploying

From the repository root:

```sh
python3 creator-sites/tools/stage-eleven-20261028.py allcapskat --check-only
python3 creator-sites/tools/stage-eleven-20261028.py allcapskat --output /tmp/allcapskat-stage-new
```

The helper verifies exact manifest hashes, creates a new staging directory outside the checkout, copies only one creator’s static runtime files, and verifies the result. It performs no network calls, Git operations, credential handling, indexing changes, or deployment. Existing output directories are refused; no files are deleted.

## Content and verification

- Eleven polished creator experiences; 79 HTML routes. Cinematic intros, media galleries, menus, themes, watchlists, share controls, local inquiry tools, and small AMH footer marks are preserved.
- 22 sourced original media links: 20 Instagram reels and two YouTube videos. Fourteen supplementary photo-story previews are separately labelled and are not represented as original social videos.
- Adina’s Instagram handle remains unresolved and her supplied Substack was unavailable. Identity was not guessed and no original reel is claimed for that creator.
- NICHA has no adult links. Existing Ashley, Isabella, and Gracie per-click age confirmations are preserved; no age response is stored. No new adult destination was added.
- Static source and mocked interaction/security tests passed. These do not establish actual responsive rendering or embedded playback. See the validation report for scope.
- Runtime catalogs contain only display/playback fields. Private research, full source screenshots, credentials, local Library identifiers, and GPS metadata are excluded. Privacy-cleaned image pixels are unchanged.

**Source publication is not final release approval.** All existing `noindex` and robots restrictions are retained; missing `noindex` tags on two legacy 404 pages were added. Actual browser QA, platform playback checks, creator-specific deployment origins, and reviewed public release remain separate steps. Do not deploy the whole repository root for one creator or remove indexing restrictions automatically. Use `[CF-Pages-Skip]` in the source-only commit message.
