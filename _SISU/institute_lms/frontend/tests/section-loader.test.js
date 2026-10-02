import assert from 'node:assert/strict'
import test from 'node:test'
import {loadSections} from '../src/lib/section-loader.js'

test('a failed section keeps its previous data and does not block successful sections', async () => {
  const result = await loadSections(
    ['applications', 'institutions', 'profiles/unassigned'],
    {applications: [{id: 'old-app'}], institutions: [{id: 'old-inst'}]},
    async path => {
      if (path === '/api/institutions') throw new Error('Institutions unavailable')
      if (path === '/api/applications') return [{id: 'new-app'}]
      return [{id: 'student-1'}]
    },
  )

  assert.deepEqual(result.data.applications, [{id: 'new-app'}])
  assert.deepEqual(result.data.institutions, [{id: 'old-inst'}])
  assert.deepEqual(result.data['profiles/unassigned'], [{id: 'student-1'}])
  assert.deepEqual(result.errors, {institutions: 'Institutions unavailable'})
})
