/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // In Docker, BACKEND_URL points to the backend service by name.
    // Locally (npm run dev), fall back to localhost.
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    return [
      {
        source: '/proxy/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
