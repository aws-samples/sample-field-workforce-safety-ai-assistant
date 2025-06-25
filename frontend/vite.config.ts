import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return {
    build: {
      target: "esnext", // Browsers can handle the latest ES features
      chunkSizeWarningLimit: 2000,
      outDir: "dist", // Set output directory for AWS Amplify hosting
    },
    plugins: [react()],
    base: '/',
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
        "@routes": path.resolve(__dirname, "src/routes"),
        "@components": path.resolve(__dirname, "src/components"),
        "@loaders": path.resolve(__dirname, "src/loaders"),
        "@lib": path.resolve(__dirname, "src/lib"),
        "./runtimeConfig": "./runtimeConfig.browser", // Alias for AWS SDK compatibility
      },
    },
    define: {
      global: "window", // Define global variable for browser compatibility
      __APP_ENV__: JSON.stringify(env.APP_ENV), // Example of environment variable usage
    },
  };
});
