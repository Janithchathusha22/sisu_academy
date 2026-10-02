// /api/me is the only source for workspace routing. Login-page choices are cosmetic.
const APPLICATION_ROLES = new Set(['student','teacher','institute_admin','super_admin'])

export function applicationRole(profile) {
  return profile?.account_status === 'active' && APPLICATION_ROLES.has(profile.application_role)
    ? profile.application_role : null
}

export function applicationRoleLabel(profile) {
  return ({student:'Student',teacher:'Teacher',institute_admin:'Institute administrator',super_admin:'Platform administrator'}[applicationRole(profile)]||'Applicant')
}

export function workspaceKind(profile) {
  if (profile?.account_status !== 'active') return 'pending'
  const role = applicationRole(profile)
  if (role === 'super_admin') return 'platform-admin'
  if (role === 'institute_admin' && profile.institution_id) return 'institute-admin'
  return 'member'
}

export function canOpenWorkspacePage(profile, page) {
  const kind = workspaceKind(profile)
  if (page === 'approvals') return kind === 'platform-admin'
  if (page === 'management') return kind === 'institute-admin'
  return true
}
