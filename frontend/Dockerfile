FROM node:22-bookworm-slim

ENV NEXT_PUBLIC_API_URL=/api
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . ./
RUN pnpm build

EXPOSE 3000
CMD ["pnpm", "start", "--", "--host", "0.0.0.0", "--port", "3000"]
