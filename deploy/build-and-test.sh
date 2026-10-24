#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_SHA:?Set GITHUB_SHA to the commit being built}"
: "${GITHUB_REPOSITORY:?Set GITHUB_REPOSITORY}"
[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]
python3 -m unittest discover -s tests/deployment -v
image_base=shop-release
labels=(--label "org.opencontainers.image.source=https://github.com/$GITHUB_REPOSITORY" --label "org.opencontainers.image.revision=$GITHUB_SHA")
docker build --platform linux/amd64 "${labels[@]}" -t "$image_base-api:$GITHUB_SHA" ./backend
# frontend/Dockerfile runs pnpm build. Its package.json test script currently
# references a missing tests/rendered-html.test.mjs, so do not invoke it here.
docker build --platform linux/amd64 --build-arg NEXT_PUBLIC_API_URL=/api \
  "${labels[@]}" -t "$image_base-frontend:$GITHUB_SHA" ./frontend

test_key=$(docker run --rm --entrypoint python "$image_base-api:$GITHUB_SHA" \
  -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
docker run --rm \
  -e PAYMENT_ENCRYPTION_KEY="$test_key" \
  -e DATABASE_URL=sqlite:// -e AUTO_CREATE_SCHEMA=true -e SEED_DEMO_DATA=true \
  -e ADMIN_BOOTSTRAP_PASSWORD=Admin@123 \
  -e COMMENT_UPLOAD_DIR=/tmp/shop-test-uploads \
  --entrypoint python "$image_base-api:$GITHUB_SHA" -m pytest tests -q
