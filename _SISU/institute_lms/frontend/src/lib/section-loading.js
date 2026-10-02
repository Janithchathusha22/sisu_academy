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
    errors[path] = response.reason?.message || 'This section could not load.'
    if (response.reason?.status === 401) authError ||= response.reason
  })

  return {values, errors, authError}
}
