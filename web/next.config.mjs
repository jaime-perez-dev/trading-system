/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // Disable ESLint during builds (we'll fix warnings later)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Allow builds to succeed even with TS errors for now
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
