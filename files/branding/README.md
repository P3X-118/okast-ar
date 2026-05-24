# okast-ar branding + instance config (saved & repeatable)

Owncast Instance Details and branding are runtime config stored only in
Owncast's SQLite DB on the host. If that DB is lost, reset, or accidentally
overwritten, the customizations are gone. These files make a deployment's
custom config **version-controlled (saved)** and **re-appliable (repeatable)**
via the admin config API. The role does NOT auto-push these (no task touches
instance config), so a normal image redeploy / `setup-service` will never
overwrite the live config — you apply these deliberately.

## Files

- `apply-instance-config.py` — idempotent apply tool. Reads an instance JSON
  and POSTs each key to `/api/admin/config/<key>` (+ optional logo / CSS).
  Run `--dry-run` first.
- `radio-cooey-instance.json` — radio.cooey.club desired-state Instance
  Details (name, summary, offline/welcome messages, page content, tags,
  nsfw, social handles). Captured live 2026-05-24.
- `radio-cooey-serverconfig.snapshot.json` — full redacted `serverconfig`
  snapshot for reference/restore (secrets stripped).
- `cooeynet-logo.jpg` — radio.cooey.club logo (800x800 JPEG, acquired
  2026-05-20). Matches the live logo as of 2026-05-24 (md5 eee19c8c…).
- `cooeynet-customstyles.css` — custom CSS injected into the page. Applied
  live as of 2026-05-24 (`--css`); pushed to the `customStyles` config field
  (`/api/admin/config/customstyles`). NOTE: verify it via the `customStyles`
  field in `serverconfig`, NOT `customStyleValues` (that field is the
  appearance color variables and is unrelated to this CSS).

## Apply (radio.cooey.club)

Admin API is reachable over the SGC mesh on epona (`169.254.0.98:8084`);
the admin password is the `sgc_pgsk`-derived value in the systemd unit.

```bash
cd files/branding
OKAST_ADMIN_PASS=<admin-pw> ./apply-instance-config.py \
    --base-url http://169.254.0.98:8084 \
    --config radio-cooey-instance.json \
    --logo cooeynet-logo.jpg
    # add --css cooeynet-customstyles.css to also push the custom CSS
```

## Re-capture current live state into the JSON

```bash
curl -s -u admin:<admin-pw> http://169.254.0.98:8084/api/admin/serverconfig \
  | python3 -c 'import sys,json;d=json.load(sys.stdin)["instanceDetails"];\
print(json.dumps({"name":d["name"],"serversummary":d["summary"],\
"offlinemessage":d["offlineMessage"],"welcomemessage":d.get("welcomeMessage",""),\
"pagecontent":d["extraPageContent"],"tags":d["tags"],"nsfw":bool(d["nsfw"]),\
"socialhandles":d.get("socialHandles") or []},indent=2))' > radio-cooey-instance.json
```
