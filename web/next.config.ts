import type { NextConfig } from "next";

// Static export: the site is plain HTML/JS reading JSON produced by the Python pipeline.
// NEXT_BASE_PATH is set in CI for GitHub Pages project sites (served from /<repo>/); empty locally.
const basePath = process.env.NEXT_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

export default nextConfig;
