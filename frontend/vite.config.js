import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Base path is relative so the built app also works from GitHub Pages or any
// sub-path, not only the domain root.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { host: "127.0.0.1", port: 5173 },
  preview: { host: "127.0.0.1", port: 4173 },
});
