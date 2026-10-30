FROM node:22-bookworm-slim AS build

WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . ./
# Precompress hashed static assets for the production server; see
# deploy/Dockerfile.frontend for the runtime reason.
RUN VINEXT_PRECOMPRESS=1 pnpm build && rm -f /app/.env.local

# Copy only the completed app, without its local configuration file.
FROM node:22-bookworm-slim
WORKDIR /app
COPY --from=build /app /app

EXPOSE 3000
CMD ["node", "node_modules/vinext/dist/cli.js", "start", "--host", "0.0.0.0", "--port", "3000"]
