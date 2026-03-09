/**
 * API base URL.
 * - In development: empty string → Vite proxy handles routing to localhost:8000
 * - In production (Vercel): set VITE_API_BASE_URL env var to your Render backend URL
 *   e.g. https://syneos-rag.onrender.com
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? '';
