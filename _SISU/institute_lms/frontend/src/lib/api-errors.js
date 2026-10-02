const SAFE_API_ERRORS = {
  0: 'Cannot connect to the server. Please try again shortly.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have permission to complete this request.',
  422: 'Some information is invalid. Check the form and try again.',
  503: 'The service is temporarily unavailable. Try again shortly.',
}

export function safeApiErrorMessage(status) {
  return SAFE_API_ERRORS[status] || 'The request could not be completed. Please try again.'
}
