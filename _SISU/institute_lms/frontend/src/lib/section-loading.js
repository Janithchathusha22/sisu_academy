export async function loadSections(paths, request) {
  const responses = await Promise.allSettled(paths.map(path=>Promise.resolve().then(()=>request(path))))
  const values = {}
  const errors = {}
  let authError

  responses.forEach((response, index) => {
    const path = paths[index]
    if (response.status === 'fulfilled') {
      values[path] = response.value
      return
    }
    const status = response.reason?.status
    errors[path] = status === 403
      ? 'Your account is not permitted to view this section.'
      : status === 503
        ? 'The server or Supabase is unavailable. Try again shortly.'
        : status === 0
          ? 'Cannot connect to the server. Check that the backend is running.'
          : response.reason?.message || 'This section could not load.'
    if (response.reason?.status === 401) authError ||= response.reason
  })

  return {values, errors, authError}
}
