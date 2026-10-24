#!/usr/bin/env bash
set -euo pipefail
umask 077

deploy_root=${1:?Usage: deploy.sh ROOT IMAGE_BASE COMMIT_SHA}
export SHOP_IMAGE_BASE=${2:?Missing image base}
export SHOP_IMAGE_TAG=${3:?Missing commit SHA}
[[ "$deploy_root" = /* && "$SHOP_IMAGE_TAG" =~ ^[0-9a-f]{40}$ ]]
release_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
command -v flock >/dev/null
exec 9>"$deploy_root/deploy.lock"
flock -w 900 9

# The server owns this configuration; it is never copied from the local .env.
set -a
source "$deploy_root/deploy.env"
set +a
: "${SHOP_COMPOSE_PROJECT:?}" "${SHOP_ENV_FILE:?}" "${SHOP_DB_VOLUME:?}" "${SHOP_UPLOAD_VOLUME:?}"
[[ "$SHOP_ENV_FILE" = /* && -f "$SHOP_ENV_FILE" ]]
compose=(docker compose --env-file "$deploy_root/deploy.env" -f "$release_dir/compose.yml")
"${compose[@]}" config --quiet

# Never create a fresh production database accidentally. This script upgrades an
# existing installation only, with the exact same project and persistent volumes.
db_id=$("${compose[@]}" ps -q db)
api_id=$("${compose[@]}" ps -q api)
[[ -n "$db_id" && -n "$api_id" ]] || { echo 'Existing db/api not found; check Compose project name.' >&2; exit 1; }
actual_db_volume=$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$db_id")
actual_upload_volume=$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/app/uploads"}}{{.Name}}{{end}}{{end}}' "$api_id")
[[ "$actual_db_volume" == "$SHOP_DB_VOLUME" && "$actual_upload_volume" == "$SHOP_UPLOAD_VOLUME" ]] || {
  echo 'Configured volumes differ from running containers; deployment stopped.' >&2; exit 1;
}
docker volume inspect "$SHOP_DB_VOLUME" "$SHOP_UPLOAD_VOLUME" >/dev/null

# Verify the source upload before building. Never download release images.
(
  cd "$release_dir"
  sha256sum --check SHA256SUMS
)
python3 "$release_dir/unpack-source.py" "$release_dir/source.tar.gz" "$release_dir/source"
bash "$release_dir/build-on-server.sh" "$release_dir" "$SHOP_IMAGE_BASE" "$SHOP_IMAGE_TAG" "$api_id" "$("${compose[@]}" ps -q frontend)"
for service in api frontend; do
  image="$SHOP_IMAGE_BASE-$service:$SHOP_IMAGE_TAG"
  actual_id=$(docker image inspect --format '{{.Id}}' "$image")
  architecture=$(docker image inspect --format '{{.Architecture}}' "$image")
  revision=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image")
  [[ "$architecture" == amd64 && "$revision" == "$SHOP_IMAGE_TAG" ]] || {
    echo "Built $service image does not match the release; stopped before migration." >&2; exit 1;
  }
  printf '%s\n' "$actual_id" > "$release_dir/$service-image.id"
done

# Check the newly required mail configuration without printing any secret values.
"${compose[@]}" run --rm --no-deps --pull never api python -c '
import os
required = ("FRONTEND_URL", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_STARTTLS")
missing = [name for name in required if not os.getenv(name)]
if missing:
    raise SystemExit("Production env is missing: " + ", ".join(missing))
from urllib.parse import urlsplit
frontend_url = urlsplit(os.environ["FRONTEND_URL"])
if frontend_url.scheme not in ("http", "https") or not frontend_url.hostname:
    raise SystemExit("FRONTEND_URL must be the public HTTP or HTTPS shop URL")
if os.environ["SMTP_PORT"] == "465":
    raise SystemExit("Current mailer uses SMTP + STARTTLS, not implicit SSL on port 465")
'

mkdir -p "$deploy_root/backups"
backup="$deploy_root/backups/$(date -u +%Y%m%dT%H%M%SZ)-$SHOP_IMAGE_TAG.sql.gz"
"${compose[@]}" exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$backup.tmp"
gzip -t "$backup.tmp"
mv "$backup.tmp" "$backup"

# Capture actual images for manual rollback, including on the first deployment.
docker inspect --format '{{.Config.Image}}' "$api_id" > "$release_dir/previous-api-image.txt"
frontend_id=$("${compose[@]}" ps -q frontend)
if [[ -n "$frontend_id" ]]; then
  docker inspect --format '{{.Config.Image}}' "$frontend_id" > "$release_dir/previous-frontend-image.txt"
fi
"${compose[@]}" run --rm --no-deps --pull never api alembic upgrade head
# Force recreation also reloads edits to the server env file for the same SHA.
"${compose[@]}" up -d --no-deps --pull never --force-recreate api frontend

healthy=false
for attempt in {1..30}; do
  if curl --fail --silent --max-time 5 http://127.0.0.1:5600/health >/dev/null \
    && curl --fail --silent --max-time 5 http://127.0.0.1:3000/api/products >/dev/null \
    && curl --fail --silent --max-time 5 http://127.0.0.1:3000/ >/dev/null; then
    healthy=true
    break
  fi
  sleep 2
done
if [[ "$healthy" != true ]]; then
  echo "Health checks failed. Inspect container logs on the server. Backup: $backup" >&2
  echo "Previous images are recorded in $release_dir. No automatic database downgrade was run." >&2
  exit 1
fi
printf '%s\n' "$SHOP_IMAGE_TAG" > "$deploy_root/deployed-sha"
ln -sfn "$release_dir" "$deploy_root/current"
# Retain manifests and rollback records, but reclaim the large transfer archive.
rm -- "$release_dir/source.tar.gz"
echo "Deployed $SHOP_IMAGE_TAG successfully. Database backup: $backup"
