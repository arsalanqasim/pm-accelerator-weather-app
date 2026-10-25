import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The frontend dev server runs on port 5173; the FastAPI backend
// (with CORS configured for this origin) runs on port 8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
