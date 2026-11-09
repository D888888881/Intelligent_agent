import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.join(__dirname, ".."), "");
  const djangoPort = env.DJANGO_PORT || "8088";
  const vitePort = parseInt(env.VITE_DEV_PORT || "3000", 10);

  return {
    plugins: [vue()],
    root: __dirname,
    envDir: path.join(__dirname, ".."),
    server: {
      host: "127.0.0.1",
      port: vitePort,
      strictPort: true,
      proxy: {
        "/api": {
          target: `http://127.0.0.1:${djangoPort}`,
          changeOrigin: true,
        },
        "/media": {
          target: `http://127.0.0.1:${djangoPort}`,
          changeOrigin: true,
        },
        "/health": {
          target: `http://127.0.0.1:${djangoPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});
