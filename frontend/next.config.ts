import type { NextConfig } from "next";

// Docker Compose resolves the `api` service name; when running `vinext dev`
// directly on the host, point API_ORIGIN at the published port instead,
// e.g. API_ORIGIN=http://127.0.0.1:5600 pnpm dev.
const apiOrigin = process.env.API_ORIGIN || "http://api:5600";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${apiOrigin}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
