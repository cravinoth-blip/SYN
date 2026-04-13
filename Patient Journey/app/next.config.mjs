/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow larger payloads for file uploads + journey JSON
  api: {
    bodyParser: {
      sizeLimit: "20mb",
    },
  },
};

export default nextConfig;
