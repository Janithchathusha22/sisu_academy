export const graphemes = text => [...new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(text || '')].length
export const lkr = value => new Intl.NumberFormat('en-LK', { style: 'currency', currency: 'LKR', maximumFractionDigits: 0 }).format(value || 0)
export const dayKey = (date = new Date()) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Colombo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date)
export const remaining = date => date ? Math.max(0, Math.round((Date.parse(date.slice(0, 10)) - Date.parse(dayKey())) / 86400000)) : null
export const billing = (count, base) => Number(base) + Math.max(0, count - 500) * 50
export function canAccess(enrollment, invoices, today = dayKey()) {
  if (!enrollment?.active) return { allowed: false, reason: 'Not enrolled' }
  if (enrollment.access_override === 'Closed') return { allowed: false, reason: 'Access closed by your institute' }
  if (enrollment.access_override === 'Open') return { allowed: true, reason: 'Opened by your institute' }
  if (!Number(enrollment.fee)) return { allowed: true, reason: 'Free classroom' }
  if (enrollment.grace_until && enrollment.grace_until >= today) return { allowed: true, reason: 'Grace period' }
  if (!invoices.length) return { allowed: false, reason: 'Payment plan pending' }
  if (invoices.some(i => i.status !== 'Paid' && i.due_date <= today)) return { allowed: false, reason: 'Payment due' }
  return { allowed: invoices.some(i => i.status === 'Paid'), reason: invoices.some(i => i.status === 'Paid') ? 'Payment up to date' : 'First payment required' }
}
export function safeLink(url) {
  try { return new URL(url).protocol === 'https:' ? url : null } catch { return null }
}
