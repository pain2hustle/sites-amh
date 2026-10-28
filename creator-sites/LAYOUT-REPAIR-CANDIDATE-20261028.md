# Creator layout repair candidate — 2026-10-28

This is a source-only candidate, not a completed visual release. Production deployments have not changed.

## Implemented
- Shared populated header with visible navigation, creator-specific social links, theme/menu controls and a primary action on all routes that have a header.
- Separate portrait and text regions on desktop and phone, bounded logo sizes, retained intro actions and small AMH footer.
- Crooked intro uses the central region of the original supplied portrait through CSS framing. Original media bytes and gallery remain preserved.
- Owner-confirmed Adina support: PayPal and Venmo, label before logo, in the hamburger menu on all seven routes and twice on the homepage. No Cash App or Zelle destination added.
- Complete original inventories retained. Indexing restrictions and age-gate scripts unchanged.

## Evidence
The reference is https://marialatinax.pages.dev and pain2hustle/marialatinax-site commit 2b37b75714c004c061728ca6350ab507cef0125f.
Before repair, Crooked and Jailyne phone headers had zero-width, display:none main links. An inherited template rule conflicted with the reserved mobile row.
Static checks cover 135 HTML routes, internal targets, original main/footer/dialog/script preservation (except explicitly approved crop/support additions), media/script bytes, external destinations, complete manifests and the existing staging workflows.
See layout-repair-static.json. Static success does not establish responsive rendering, native playback or visual acceptance.

## Support destination provenance
Both public pages visibly identify Adina Flores and @civilrights707:
- https://www.paypal.com/paypalme/civilrights707
- https://venmo.com/u/civilrights707

PayPal logo: https://www.paypalobjects.com/marketing/web/logos/paypal-mark-color_new.svg, observed on the verified public PayPal page. Venmo logo reused unchanged from the documented Maria source. No sign-in or transaction was performed.

## Required before publication
The owner's later instruction requires the established cloner using Maria's actual source. This corrective overlay is not a substitute for that requirement.
The existing clone_creator.py accepts Lucas/Matty/Quinn bases and expects brand-config.json, assets/socials.json and specific replacement markers missing from current Maria source. It needs a reviewed Maria-source adapter; do not silently select a derivative.
Visual review at 320, 360, 390 and desktop widths remains pending. The local file URL preview was rejected by browser policy; that route was stopped. No alternate transport was used.
Preserve current deployment versions, review complete output and use the dedicated approved Pages route only after required checks pass. No automatic deployment is triggered by this source branch.
