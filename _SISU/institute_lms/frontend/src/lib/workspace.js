// /api/me is the only source for workspace routing. Login-page choices are cosmetic.
const APPLICATION_ROLES = new Set(['student','teacher','institute_admin','super_admin'])
const SHARED_LEARNING = ['dashboard','classes','courses','learning','schedule','attendance','assignments','materials','exams','results','notifications','profile']
const ROLE_PAGES = {
  student: new Set([...SHARED_LEARNING,'payments']),
  teacher: new Set(SHARED_LEARNING),
  institute_admin: new Set([...SHARED_LEARNING,'payments','management']),
  super_admin: new Set([...SHARED_LEARNING,'payments','approvals']),
}

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
  const role = applicationRole(profile)
  if (role === 'institute_admin' && !profile.institution_id) return page === 'profile'
  return ROLE_PAGES[role]?.has(page) || false
}
