// Deliberately unavailable in production builds or on a non-loopback host.
export const previewMode = import.meta.env.DEV && ['localhost','127.0.0.1','[::1]'].includes(location.hostname) && new URLSearchParams(location.search).get('preview') === '1'
