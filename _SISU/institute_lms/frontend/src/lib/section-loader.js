export async function loadSections(paths, previousData, request) {
  const results = await Promise.allSettled(paths.map(path => request('/api/' + path)))
  const data = {...previousData}
  const errors = {}
  results.forEach((result, index) => {
    const path = paths[index]
    if (result.status === 'fulfilled') data[path] = result.value
    else errors[path] = result.reason?.message || 'This section could not load. Please try again.'
  })
  return {data, errors}
}
