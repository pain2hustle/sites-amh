# Actual Maria frontend adapter — review candidate

This adds `--base maria` to an isolated copy of the established AMH cloner. The shared original cloner is untouched. The reference is the public Maria page captured on 2026-10-28, whose layout differs from Git reference 2b37b75714c004c061728ca6350ab507cef0125f. See PROVENANCE.json.

The adapter imports Maria's actual header/menu/profile/intro hierarchy and current layout CSS, preserves the creator's complete routes, media catalog, forms, age gates, watchlist, dialogs and JavaScript, and renders creator-specific wordmarks with the existing cloner's Fredoka pipeline. Rendering runs sequentially with supersampling reduced to 1 to bound memory use. Original assets remain in each output. Generated wordmarks are design treatments, not claimed official creator logos.

Run from this directory (Python with BeautifulSoup, Pillow, NumPy and SciPy already installed):

    python clone_creator.py recipes/thecrookedman10.json D:/AMH/CreatorReleases/NEW-CANDIDATE/thecrookedman10 --base maria --no-commit
    python validate_candidates.py D:/AMH/CreatorReleases/NEW-CANDIDATE

Every output directory must be new. The mode does not push, deploy, or provision backend services. Other inherited cloner modes are not packaged as standalone workflows here. Browser QA uses the supported computer-use connection, never the inherited external browser-check helper.

## Evidence

The 12 local candidates retained 135 HTML routes / 681 files. Internal links, local assets, imported CSS URLs, donor identity leakage, original script lists, original external URLs and original non-HTML/CSS payload bytes were checked. Existing robots metadata is unchanged; the eleven-site noindex hold is intentional pending reviewed release. Jailyne's existing indexing metadata is preserved exactly.

At 390×844, Adina, Allcapskat, Anna, Ashley, Danny, Gracie and Immapeaches passed: populated 112px header; no document overflow; loaded image sources; menu open; Escape close; trigger focus restored. Crooked separately passed 390px and 1366px visual layout inspection and menu focus restoration. Jailyne's phone layout was visually inspected, but its full interaction pass is pending.

The inspection caught and corrected overflowing social labels, hamburger bars positioned against the page instead of their button, dark social icons, and an inherited stage background that became inappropriate after the donor artwork substitution. Crooked's original supplied portrait is framed to exclude the screenshot captions; no face/image content was invented.

## Not yet verified or published

No Maria-adapted candidate has been deployed. Remaining: visual review across all breakpoints and routes, player cleanup, all unique image/link checks, age-gate cancel/reopen, theme checks, and screenshots retained as artifacts. The browser connection timed out while opening Isatobaa; local servers independently returned HTTP 200. Recovery through the documented existing tab and fresh-tab routes also timed out. This is an execution/connection failure, not a denied permission action.

The adapter retains each creator's existing frontend functionality. It does not clone Maria's account database, owner editor, customer/orders data, checkout bindings, email/SMS recipients or backend credentials. Those features cannot be represented as connected merely by copying a frontend. Ashley and Sherry keep their functional native dialog menu/player contracts; complete visual parity of their alternate sections still needs review.

India has a separate local intake/builder outside this repository: 13 published URLs across 11 platforms, ordered full-video requirements, and no copied donor payment accounts. Original full videos remain required; the confirmed Hoo.be portrait download returned HTTP 403; two different Kick handles remain unresolved. No India build or publication is claimed complete.
