import type { NextConfig } from "next";

// Static export: the site is plain HTML/JS reading JSON produced by the Python pipeline.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
