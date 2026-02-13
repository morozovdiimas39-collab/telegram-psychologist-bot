import {defineConfig} from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
// import {componentTagger} from "pp-tagger"; // ОТКЛЮЧЕНО — может мешать

// https://vitejs.dev/config/
export default defineConfig(({mode}) => ({
    plugins: [
        react(),
        // mode === 'development' && componentTagger(), // ОТКЛЮЧЕНО
    ].filter(Boolean),
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        host: '127.0.0.1',
        port: 5173,
        allowedHosts: true,
        hmr: {
            overlay: false // Disables the error overlay if you only want console errors
        }
    },
}));
