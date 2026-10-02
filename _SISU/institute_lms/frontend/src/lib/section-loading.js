import {safeApiErrorMessage} from './api-errors.js'

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
    errors[path] = status
      ? safeApiErrorMessage(status)
      : 'This section could not load. Please try again.'
    if (response.reason?.status === 401) authError ||= response.reason
  })

  return {values, errors, authError}
}

export function mergeSectionResults(currentValues, currentErrors, paths, result) {
  const values = {...currentValues}
  const errors = {...currentErrors}

  for (const path of paths) {
    if (Object.hasOwn(result.values, path)) {
      values[path] = result.values[path]
      delete errors[path]
    } else if (Object.hasOwn(result.errors, path)) {
      errors[path] = result.errors[path]
    }
  }

  return {values, errors}
}
