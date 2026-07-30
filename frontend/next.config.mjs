/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (process.env.VERCEL && !process.env.DAYBOOK_API_ORIGIN) {
      throw new Error("DAYBOOK_API_ORIGIN is required on Vercel.");
    }
    const backendOrigin = (
      process.env.DAYBOOK_API_ORIGIN ?? "http://127.0.0.1:8000"
    ).replace(/\/+$/, "");

    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
