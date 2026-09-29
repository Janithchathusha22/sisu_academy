import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  base: command === 'build' ? '/assets/institute_lms/portal/' : '/',
  build: { outDir: '../institute_lms/public/portal', emptyOutDir: true },
  server: { port: 5178, strictPort: true,
    // Optional same-origin development bridge; set only to your own Frappe site.
    proxy: process.env.SISU_FRAPPE_URL ? Object.fromEntries(['/api','/login','/me','/files','/private','/assets/frappe'].map(path=>[path,{target:process.env.SISU_FRAPPE_URL,changeOrigin:true}])) : undefined },
}))
