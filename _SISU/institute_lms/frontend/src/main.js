import { createApp } from 'vue'
import App from './native/PortalRoot.vue'
import './style.css'
// Only retired fictional workspace stores are removed. Personal notes, uploaded
// files, browser preferences and server records are not touched.
for (const key of ['sisu-demo-v2','sisu-community-v1','sisu-wallet-preview-v1']) {
  try { localStorage.removeItem(key) } catch { /* Private browsing may deny storage. */ }
}
createApp(App).mount('#app')
