#!/usr/bin/env python3
"""Idempotently apply Owncast (okast) Instance Details + branding from
version-controlled files, via the admin config API.

This makes a deployment's "custom changes" (server name, summary, tags,
offline/welcome messages, page content, social handles, logo, custom CSS)
SAVED (in git, next to this script) and REPEATABLE (re-run any time to
restore them). Runtime instance config otherwise lives only in Owncast's
SQLite DB on the host; this is the recover/redeploy path if that DB is
ever lost or accidentally overwritten.

Each key in the --config JSON maps 1:1 to POST /api/admin/config/<key>
with body {"value": <v>} (the shape every Owncast admin setter expects).
Logo and CSS are applied from separate files (binary / large text).

radio.cooey.club example (admin API reachable over the SGC mesh on epona):

  ./apply-instance-config.py \
      --base-url http://169.254.0.98:8084 \
      --admin-pass "$ADMIN_PASS" \
      --config radio-cooey-instance.json \
      --logo cooeynet-logo.jpg
      # add --css cooeynet-customstyles.css to also push the custom CSS

Run with --dry-run first to see exactly what would change.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

# config.json keys that are applied verbatim as {"value": <json value>}.
# (logo and customstyles come from separate files via flags.)
SCALAR_KEYS = [
    "name",
    "serversummary",
    "offlinemessage",
    "welcomemessage",
    "pagecontent",
    "tags",
    "nsfw",
    "socialhandles",
]

EXT_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".svg": "image/svg+xml"}


def post(base_url, admin_pass, key, value, dry_run):
    url = f"{base_url.rstrip('/')}/api/admin/config/{key}"
    body = json.dumps({"value": value}).encode()
    shown = value if not isinstance(value, str) else (value[:70] + ("…" if len(value) > 70 else ""))
    if dry_run:
        print(f"  DRY-RUN {key}: {shown!r}")
        return True
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    token = base64.b64encode(f"admin:{admin_pass}".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            out = json.loads(resp.read().decode() or "{}")
            ok = out.get("success", resp.status == 200)
            print(f"  {'OK ' if ok else 'FAIL'} {key}: {shown!r}" + ("" if ok else f"  -> {out}"))
            return ok
    except urllib.error.HTTPError as e:
        print(f"  FAIL {key}: HTTP {e.code} {e.read().decode()[:120]}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {key}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=os.environ.get("OKAST_BASE_URL", "http://169.254.0.98:8084"))
    ap.add_argument("--admin-pass", default=os.environ.get("OKAST_ADMIN_PASS", ""))
    ap.add_argument("--config", default="radio-cooey-instance.json")
    ap.add_argument("--logo", help="image file to apply as the instance logo")
    ap.add_argument("--css", help="CSS file to apply as custom styles")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.admin_pass and not args.dry_run:
        sys.exit("error: --admin-pass (or OKAST_ADMIN_PASS) is required")

    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = args.config if os.path.isabs(args.config) else os.path.join(here, args.config)
    cfg = json.load(open(cfg_path))

    print(f"Applying instance config from {os.path.basename(cfg_path)} -> {args.base_url}")
    results = []
    for key in SCALAR_KEYS:
        if key in cfg:
            results.append(post(args.base_url, args.admin_pass, key, cfg[key], args.dry_run))

    if args.logo:
        logo_path = args.logo if os.path.isabs(args.logo) else os.path.join(here, args.logo)
        ext = os.path.splitext(logo_path)[1].lower()
        mime = EXT_MIME.get(ext, "image/jpeg")
        data = base64.b64encode(open(logo_path, "rb").read()).decode()
        results.append(post(args.base_url, args.admin_pass, "logo", f"data:{mime};base64,{data}", args.dry_run))

    if args.css:
        css_path = args.css if os.path.isabs(args.css) else os.path.join(here, args.css)
        results.append(post(args.base_url, args.admin_pass, "customstyles", open(css_path).read(), args.dry_run))

    failed = results.count(False)
    print(f"\nDone: {len(results) - failed}/{len(results)} applied" + (f", {failed} FAILED" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
