import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Base public path — must match the path at which CDS serves the built UI.
  // CDS auto-serves static files from app/<subdir> at /<subdir>/,
  // so we output to app/react-ui/ and set base accordingly.
  base: '/react-ui/',
  build: {
    outDir: '../app/react-ui',
    emptyOutDir: true
  },
  plugins: [react()],
  server: {
    port: 5173,
    // Fix WebSocket HMR for cloud-based IDEs (SAP BAS / agent-sandbox).
    // The proxy tunnels HTTP on port 443 with wss://, so we must tell
    // Vite's HMR client to connect on port 443 over a secure WebSocket
    // instead of trying to open a raw ws:// connection directly.
    hmr: {
      protocol: 'wss',
      clientPort: 443
    },
    proxy: {
      // Proxy all OData + risk service calls to the local CAP server
      '/risk':      'http://localhost:4004',
      '/odata':     'http://localhost:4004',
      '/$metadata': 'http://localhost:4004',
    }
  }
})
