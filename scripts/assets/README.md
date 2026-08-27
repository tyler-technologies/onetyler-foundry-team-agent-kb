# Brand assets

Copied **byte-for-byte** from the Ops Center repo so the review UI wears the same Tyler
"talking Ts" mark as the product it reviews:

| File | Source in `tcp-ops-center` | Use |
|---|---|---|
| `tyler-brand-dark-theme.svg` | `tcp-ops-center/wwwroot/images/tyler-brand-dark-theme.svg` | white mark — for the dark app bar. This is the one the review UI serves at `/logo.svg`. |
| `tyler-brand-light-theme.svg` | `tcp-ops-center/wwwroot/images/tyler-brand-light-theme.svg` | full-colour mark (`#40528F`, `#817C00`, `#999332`) — for a light background. Kept for when the UI grows a light header or a print view. |

**Do not "clean up" these files.** They are a brand mark, and staying identical to the
upstream copy is the point — it is what makes a diff against Ops Center meaningful and keeps
the two products visually consistent. In particular:

- The `®` glyph is a `<text>` element in `ArialMT`. At app-bar size it is barely a pixel, and
  deleting it would be a branding decision, not a rendering fix. Left alone deliberately.
- The Adobe Illustrator generator comment and the SVG 1.1 DOCTYPE are noise, but removing
  them would make these no longer byte-identical to their source for no real gain.

Both are `viewBox="0 0 96 96"`, so they scale cleanly to any size.

Refresh them if Ops Center ever rebrands:

```bash
B=<path to>/tcp-ops-center/tcp-ops-center/wwwroot/images
cp "$B/tyler-brand-dark-theme.svg" "$B/tyler-brand-light-theme.svg" scripts/assets/
```
