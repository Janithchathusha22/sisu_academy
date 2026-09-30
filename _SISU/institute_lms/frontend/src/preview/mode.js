// Standalone builds use browser-only fictional data, without a Frappe session.
// Normal Frappe production builds cannot enable preview through URL parameters.
export const standaloneMode = import.meta.env.MODE === 'standalone'
export const previewMode = standaloneMode || (import.meta.env.DEV && ['localhost','127.0.0.1','[::1]'].includes(location.hostname) && new URLSearchParams(location.search).get('preview') === '1')
