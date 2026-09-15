import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Port 8100 is the SPA redirect URI registered on the reviewer Entra app, so
// strictPort keeps a silent fallback to 8101 from breaking sign-in locally.
// The API proxy targets 8101 rather than web-chat's 8000 so both surfaces can
// run at the same time.
export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 8100,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8101' },
  },
});
