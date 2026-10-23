import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev (`npm run dev`) the API lives on :8000; in Docker nginx does this proxying (see nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
