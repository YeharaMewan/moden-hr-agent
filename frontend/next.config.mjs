/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    outputFileTracingRoot: undefined,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api',
  },
  // For production optimization
  compress: true,
  poweredByHeader: false,
  generateEtags: false,
  // Handle trailing slashes
  trailingSlash: false,
}

export default nextConfig