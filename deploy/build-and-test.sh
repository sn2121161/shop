#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_SHA:?Set GITHUB_SHA to the commit being built}"
: "${GITHUB_REPOSITORY:?Set GITHUB_REPOSITORY}"
[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]
python3 -m unittest discover -s tests/deployment -v
image_base=shop-release
labels=(--label "org.opencontainers.image.source=https://github.com/$GITHUB_REPOSITORY" --label "org.opencontainers.image.revision=$GITHUB_SHA")
docker build --platform linux/amd64 "${labels[@]}" -t "$image_base-api:$GITHUB_SHA" ./backend
# frontend/Dockerfile runs the production build.
docker build --platform linux/amd64 \
  "${labels[@]}" -t "$image_base-frontend:$GITHUB_SHA" ./frontend

docker run --rm --network none --entrypoint sh "$image_base-frontend:$GITHUB_SHA" -c \
  'node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js . --ignore-pattern dist --ignore-pattern .next'

# Exercise the production SSR entry: a successful build and homepage alone
# do not detect missing runtime imports in lazily loaded product pages.
docker run --rm -i --network none --entrypoint node "$image_base-frontend:$GITHUB_SHA" - <<'JS'
const { spawn } = require("node:child_process");
const server = spawn(process.execPath, ["node_modules/vinext/dist/cli.js", "start", "--host", "0.0.0.0", "--port", "3000"], { stdio: "inherit" });
const deadline = Date.now() + 15000;
(async () => {
  try {
    for (const path of ["/", "/products/1", "/cart", "/tracking", "/login", "/register", "/admin"]) {
      let response;
      while (!response) {
        try {
          response = await fetch(`http://127.0.0.1:3000${path}`, { signal: AbortSignal.timeout(5000) });
        } catch (error) {
          if (Date.now() >= deadline || server.exitCode !== null) throw error;
          await new Promise((resolve) => setTimeout(resolve, 200));
        }
      }
      const html = await response.text();
      if (response.status !== 200 || html.includes('id="__next_error__"')) {
        throw new Error(`Production SSR failed for ${path}: HTTP ${response.status}`);
      }
      console.log(`Production SSR passed: ${path}`);
    }
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  } finally {
    server.kill("SIGTERM");
  }
})();
JS

test_key=$(docker run --rm --entrypoint python "$image_base-api:$GITHUB_SHA" \
  -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
docker run --rm \
  -e PAYMENT_ENCRYPTION_KEY="$test_key" \
  -e DATABASE_URL=sqlite:// -e AUTO_CREATE_SCHEMA=true -e SEED_DEMO_DATA=true \
  -e ADMIN_BOOTSTRAP_PASSWORD=Admin@123 \
  -e COMMENT_UPLOAD_DIR=/tmp/shop-test-uploads \
  --entrypoint python "$image_base-api:$GITHUB_SHA" -m pytest tests -q
