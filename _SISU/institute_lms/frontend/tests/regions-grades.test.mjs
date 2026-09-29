import test from 'node:test'
import assert from 'node:assert/strict'
import {regions,menaCountries} from '../src/regions.js'
import {educationPresets,marketplaceSeed,validateProvider} from '../src/marketplace.js'
import {calculateGpa} from '../src/grades.js'
test('Middle East presets offer curricula independently of country',()=>{
 for(const country of menaCountries){assert(regions[country]);assert(educationPresets[country].some(s=>s.startsWith('British')));assert(educationPresets[country].includes('International Baccalaureate'));assert.doesNotThrow(()=>new Intl.DateTimeFormat('en',{timeZone:regions[country].timezone}).format())}
 const m=marketplaceSeed(),uae=m.providers.find(p=>p.country==='United Arab Emirates');assert.equal(uae.currency,'AED');assert.equal(uae.timezone,'Asia/Dubai');assert.equal(m.classes.filter(c=>c.provider===uae.name).length,2)
})
test('provider validation rejects invalid time zones and website credentials',()=>{
 const p={...marketplaceSeed().providers[0],username:'testacademy'}
 assert.throws(()=>validateProvider({...p,timezone:'Not/AZone'},[]));assert.throws(()=>validateProvider({...p,website:'https://name:secret@example.com'},[]))
})
test('GPA weights credits, includes failed courses and excludes pass/fail courses',()=>{
 const v=calculateGpa([{credits:3,points:4},{credits:1,points:0},{credits:5,points:1,excluded:true}]);assert.equal(v.gpa,3);assert.equal(v.credits,4);assert.equal(calculateGpa([]).gpa,null)
})
test('GPA rejects malformed, negative or out-of-scale values',()=>{
 for(const row of [{credits:0,points:4},{credits:3,points:''},{credits:3,points:5},{credits:'oops',points:3},{credits:3,points:-1}])assert.throws(()=>calculateGpa([row]))
})
