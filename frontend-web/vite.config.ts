import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { PAGES, landingHtml } from "./landings.mjs";

const root = dirname(fileURLToPath(import.meta.url));

function landingPages() {
  return {
    name: "landing-pages",
    transformIndexHtml(html) {
      return html.replace("<!--LANDING--><!--/LANDING-->", `<!--LANDING-->${landingHtml(PAGES.home)}<!--/LANDING-->`);
    },
    closeBundle() {
      const indexPath = resolve(root, "dist/index.html");
      const index = readFileSync(indexPath, "utf8");
      for (const page of Object.values(PAGES)) {
        if (!page.file) continue;
        const html = index
          .replace(/<title>[\s\S]*?<\/title>/, `<title>${page.title}</title>`)
          .replace(/<meta name="description" content="[\s\S]*?" \/>/, `<meta name="description" content="${page.description}" />`)
          .replace(/<!--LANDING-->[\s\S]*?<!--\/LANDING-->/, `<!--LANDING-->${landingHtml(page)}<!--/LANDING-->`);
        writeFileSync(resolve(root, "dist", page.file), html);
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), landingPages()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/static": "http://127.0.0.1:8000",
    },
  },
});
