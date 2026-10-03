const SAFE_API_ERRORS = {
  0: 'Cannot connect to the server. Please try again shortly.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have permission to complete this request.',
  422: 'Some information is invalid. Check the form and try again.',
  503: 'The service is temporarily unavailable. Try again shortly.',
}

const SAFE_API_ERROR_CODES = {
  authentication_required: 'Please sign in to continue.',
  session_expired: 'Your session has expired. Please sign in again.',
  session_rejected: 'Your sign-in session is no longer valid. Please sign in again.',
  session_invalid: 'Your sign-in session is invalid. Please sign in again.',
  session_project_mismatch: 'This session belongs to a different SISU project. Please sign in again.',
  session_not_yet_valid: "Your session is not valid yet. Check this computer's UTC clock and try again.",
  profile_pending: 'Your application is awaiting approval. Refresh after an administrator reviews it.',
  profile_missing: 'Your application profile has not been created yet. Contact the administrator.',
  profile_provisioning_unavailable: 'Profile setup is temporarily unavailable. Contact the administrator.',
  account_rejected: 'Your application was not approved. Contact the administrator if this is unexpected.',
  account_suspended: 'Your account is suspended. Contact the administrator.',
  account_not_approved: 'Your account is not approved for this workspace.',
  auth_service_unavailable: 'The sign-in service is temporarily unavailable. Try again shortly.',
  token_verification_unavailable: 'Session verification is temporarily unavailable. Try again shortly.',
  database_unavailable: 'The database is temporarily unavailable. Try again shortly.',
  upstream_unavailable: 'A required service is temporarily unavailable. Try again shortly.',
  server_configuration: 'Server configuration is incomplete. Contact the administrator.',
  permission_denied: 'You do not have permission to complete this request.',
}

export function safeApiErrorMessage(status, code = '', context = {}) {
  if (code === 'session_not_yet_valid' && Number.isInteger(context.clock_skew_seconds) && context.clock_skew_seconds > 0) {
    return `Your system UTC clock is behind by about ${context.clock_skew_seconds} seconds. Correct it and try again.`
  }
  if (Object.hasOwn(SAFE_API_ERROR_CODES, code)) return SAFE_API_ERROR_CODES[code]
  return SAFE_API_ERRORS[status] || 'The request could not be completed. Please try again.'
}
