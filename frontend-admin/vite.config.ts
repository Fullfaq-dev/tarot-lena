import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/admin-api": "http://api:8000",
      "/static": "http://api:8000",
    },
  },
});
