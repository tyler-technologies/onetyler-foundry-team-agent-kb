#!/usr/bin/env python3
"""Measure foreground/background contrast in the review UI, in BOTH display modes.

Why this exists. Adding dark mode means every accent colour inverts: Forge's light primary
`#3f51b5` is dark and takes white text, while its dark primary `#8c9eff` is light and does
NOT. A rule reading

    button { background: var(--forge-theme-primary); color: #fff }

is correct in light and unreadable in dark, and it looks obviously right in both. Measured
when dark mode was added on 2026-08-27: white text on the dark-mode accents came out at
primary 2.49:1, warning 1.75:1, success 1.96:1, error 2.01:1 - all far under 4.5:1. The fix
was an `--on-accent` token; this file is what stops the next one shipping.

It resolves the `:root` and `[data-mode="dark"]` token tables, then for every rule that sets
both a background and a colour, computes the ratio under each mode.

    python3 scripts/check_contrast.py            # fail on anything under threshold
    python3 scripts/check_contrast.py --list     # print every pair it measured

Deliberately conservative about what it claims: it only judges rules where BOTH properties
are in the same declaration block, since that is the only case where the pairing is certain.
A colour inherited from an ancestor is out of scope, so a PASS here is not proof the whole
page is legible - it is proof that no rule contradicts itself.
"""
import argparse
import importlib.util
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
AA_NORMAL, AA_LARGE = 4.5, 3.0

# Rules whose text is large enough for the 3:1 large-text threshold, or where the pairing is
# decorative rather than text. Keyed by selector substring, with the reason required.
LARGE_TEXT = {
    ".kpi .v": "26px 600-weight numeral - large text by WCAG",
    "header b": "16px 500-weight on a 56px bar - the app title",
}


def _srgb(c):
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def token_table(css, selector):
    """The variables declared in one block, as {name: raw value}."""
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n\}", css, re.S)
    if not m:
        return {}
    out = {}
    for name, val in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1)):
        out[name] = val.strip()
    return out


def resolve(val, table, depth=0):
    """Follow var() chains to a literal colour, or None if it is not a plain colour.

    rgba() is returned as None on purpose: a translucent colour's effective contrast depends
    on what is behind it, and guessing would produce confident nonsense.
    """
    if depth > 8 or not val:
        return None
    val = val.strip()
    m = re.fullmatch(r"var\((--[\w-]+)(?:\s*,\s*(.+))?\)", val)
    if m:
        name, fallback = m.group(1), m.group(2)
        if name in table:
            return resolve(table[name], table, depth + 1)
        return resolve(fallback, table, depth + 1) if fallback else None
    if re.fullmatch(r"#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{6}", val):
        return val
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print every measured pair")
    a = ap.parse_args()

    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location("review_server",
                                                 REPO / "scripts" / "review_server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    css = mod.CSS

    light = token_table(css, ":root")
    dark_overrides = token_table(css, '[data-mode="dark"]')
    dark = dict(light)
    dark.update(dark_overrides)
    # Sanity-check by counting OVERRIDES, not the merged size. The merged dict is the same
    # length as light whenever dark only re-declares names that already exist - which is
    # exactly what a correct dark block does, so a size comparison here reports a healthy
    # stylesheet as broken. (It did, on the first run of this file.)
    if not light or not dark_overrides:
        print("FAIL: could not read both token tables — has the CSS been restructured?",
              file=sys.stderr)
        return 1

    # Every declaration block that sets BOTH a background and a colour.
    pairs = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        sel = " ".join(sel.split())
        if sel.startswith(("@", ":root")) or "data-mode" in sel:
            continue
        bg = re.search(r"(?:^|;|\s)background(?:-color)?\s*:\s*([^;]+)", body)
        fg = re.search(r"(?:^|;|\s)color\s*:\s*([^;]+)", body)
        if bg and fg:
            pairs.append((sel, fg.group(1).strip(), bg.group(1).strip()))

    fails, measured, skipped = [], 0, 0
    for sel, fg_raw, bg_raw in pairs:
        thresh, why = AA_NORMAL, ""
        for key, reason in LARGE_TEXT.items():
            if key in sel:
                thresh, why = AA_LARGE, reason
        for mode, table in (("light", light), ("dark", dark)):
            fg, bg = resolve(fg_raw, table), resolve(bg_raw, table)
            if not fg or not bg:
                skipped += 1
                continue
            measured += 1
            r = ratio(fg, bg)
            if a.list:
                print(f"  {mode:5} {r:5.2f}:1  {sel[:44]:44} {fg} on {bg}")
            if r < thresh:
                fails.append((mode, sel, fg, bg, r, thresh, why))

    if fails:
        print(f"FAIL: {len(fails)} rule(s) below the contrast threshold:", file=sys.stderr)
        for mode, sel, fg, bg, r, thresh, why in fails:
            print(f"  [{mode}] {r:.2f}:1 (need {thresh}:1)  {sel}\n"
                  f"          {fg} on {bg}"
                  + (f"   [{why}]" if why else ""), file=sys.stderr)
        print("\n  If the fill is a mode-dependent accent, the fix is `color:var(--on-accent)`,"
              "\n  not a hardcoded #fff — see the token's comment in review_server.py.",
              file=sys.stderr)
        return 1

    # An inline style is invisible to everything above, and cannot respond to [data-mode] at
    # all - so a hardcoded colour there is not merely unmeasured, it is guaranteed not to flip.
    # This is how three review banners shipped as light-green panels that kept their tint in
    # dark mode while their text went light: found by LOOKING at the page, not by any check,
    # which is why the check now exists.
    src = (REPO / "scripts" / "review_server.py").read_text(encoding="utf-8")
    inline = []
    for m in re.finditer(r"""style=(['"])(.*?)\1""", src):
        decl = m.group(2)
        if not re.search(r"(?:^|;|\s)(?:background|border-color|color)\s*:", decl):
            continue
        for lit in re.findall(r"#[0-9A-Fa-f]{3,6}\b", decl):
            line = src[:m.start()].count("\n") + 1
            inline.append((line, lit, decl[:70]))
    if inline:
        print(f"FAIL: {len(inline)} hardcoded colour(s) in an INLINE style — these cannot "
              f"respond to [data-mode] and will not flip in dark mode:", file=sys.stderr)
        for line, lit, decl in inline:
            print(f"  review_server.py:{line}  {lit}  in  style=\"{decl}\"", file=sys.stderr)
        print("\n  Move it to a class in CSS and give it a token per mode. A tinted panel must\n"
              "  also state its own `color` — inheriting it is what breaks, because the ink\n"
              "  follows the mode while the inline panel does not.", file=sys.stderr)
        return 1

    print(f"Contrast OK: {measured} foreground/background pair(s) measured across light and "
          f"dark, none under threshold.")
    print(f"  ({skipped} skipped — translucent or non-colour values, where a ratio would be "
          f"a guess.)")
    print("  No hardcoded colours in inline styles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
