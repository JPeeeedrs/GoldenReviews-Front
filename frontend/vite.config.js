import { resolve } from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
	plugins: [react()],
	server: {
		proxy: {
			"/steamspy": {
				target: "https://steamspy.com",
				changeOrigin: true,
				secure: true,
				rewrite: (path) => path.replace(/^\/steamspy/, ""),
			},
		},
	},
	build: {
		rollupOptions: {
			input: {
				main: resolve(__dirname, "index.html"),
				topics: resolve(__dirname, "topics.html"),
				games: resolve(__dirname, "games.html"),
			},
		},
	},
});
