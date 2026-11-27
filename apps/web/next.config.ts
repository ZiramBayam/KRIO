import type { NextConfig } from "next";

// Static export: nginx on the demo VM serves `out/` and proxies /api to FastAPI,
// so the dashboard and API share one origin and no Node server runs in production.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
