// /api/me is the only source for workspace routing. Login-page choices are cosmetic.
export function workspaceKind(profile) {
  if (profile?.account_status !== 'active') return 'pending'
  if (profile.role === 'super_admin') return 'platform-admin'
  if (profile.role === 'institute_admin' && profile.institution_id) return 'institute-admin'
  return 'member'
}

export function canOpenWorkspacePage(profile, page) {
  const kind = workspaceKind(profile)
  if (page === 'approvals') return kind === 'platform-admin'
  if (page === 'management') return kind === 'institute-admin'
  return true
}
