/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api',
  },
  // Production optimizations
  compress: true,
  poweredByHeader: false,
  generateEtags: false,
  trailingSlash: false,
}

export default nextConfig