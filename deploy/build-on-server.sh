#!/usr/bin/env bash
set -euo pipefail

release_dir=${1:?Usage: build-on-server.sh RELEASE_DIR IMAGE_BASE COMMIT_SHA API_CONTAINER FRONTEND_CONTAINER}
image_base=${2:?}
revision=${3:?}
api_container=${4:?}
frontend_container=${5:?}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]]
source_dir="$release_dir/source"
[[ -d "$source_dir/backend" && -d "$source_dir/frontend" ]]

# Application configuration stays on the server, separate from deployment settings.
frontend_env_file="${SHOP_FRONTEND_ENV_FILE:-$(dirname "$release_dir")/frontend/.env.local}"
if [[ -f "$frontend_env_file" ]]; then
  cp -- "$frontend_env_file" "$source_dir/frontend/.env.local"
  chmod 600 "$source_dir/frontend/.env.local"
fi

# One-time, offline seed from images already on this server. Pin by container
# image ID, not a mutable release tag. Retain these tags when pruning images.
for service in api frontend; do
  base="shop-build-$service:bootstrap"
  if ! docker image inspect "$base" >/dev/null 2>&1; then
    if [[ "$service" == api ]]; then container="$api_container"; else container="$frontend_container"; fi
    image_id=$(docker inspect --format '{{.Image}}' "$container")
    docker image tag "$image_id" "$base"
  fi
  [[ $(docker image inspect --format '{{.Architecture}}' "$base") == amd64 ]]
done

labels=(--label "org.opencontainers.image.revision=$revision")
docker build --pull=false --memory=1536m "${labels[@]}" \
  --build-arg "PIP_INDEX_URL=${SHOP_PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}" \
  -f "$source_dir/deploy/Dockerfile.api" -t "$image_base-api:$revision" "$source_dir/backend"
docker build --pull=false --memory=1536m "${labels[@]}" \
  --build-arg "NPM_REGISTRY=${SHOP_NPM_REGISTRY:-https://registry.npmmirror.com}" \
  -f "$source_dir/deploy/Dockerfile.frontend" -t "$image_base-frontend:$revision" "$source_dir/frontend"

# Validate the server-built backend before any backup, migration or service swap.
test_key=$(docker run --rm --network none --entrypoint python "$image_base-api:$revision" \
  -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
docker run --rm --network none \
  -e PAYMENT_ENCRYPTION_KEY="$test_key" -e DATABASE_URL=sqlite:// \
  -e AUTO_CREATE_SCHEMA=true -e SEED_DEMO_DATA=true -e ADMIN_BOOTSTRAP_PASSWORD=Admin@123 \
  -e COMMENT_UPLOAD_DIR=/tmp/shop-test-uploads \
  --entrypoint python "$image_base-api:$revision" -m pytest tests -q -p no:cacheprovider
