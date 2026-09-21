import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
const target = process.env.NEIGHBORFOOD_BACKEND || "http://127.0.0.1:8000";
const proxy = Object.fromEntries(
  [
    "/api",
    "/posts",
    "/uploads",
    "/upload-images",
    "/logout",
    "/request-auth",
    "/reset-password",
  ].map((path) => [path, { target, changeOrigin: true }]),
);
export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
});
