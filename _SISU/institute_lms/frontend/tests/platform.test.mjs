import test from 'node:test'
import assert from 'node:assert/strict'
import {marketplaceSeed,nextProviderCode,validateProvider,youtubeVideoId} from '../src/marketplace.js'
import {prunePromotions,platformSummary} from '../src/platform.js'
import {seed} from '../src/demoExpanded.js'
test('public usernames and institute codes are distinct and collision checked',()=>{
 const {providers}=marketplaceSeed();assert.equal(providers[0].username,'teenacademysl');assert.equal(providers[0].code,'TA0051');assert.equal(nextProviderCode('Teen Academy',providers),'TA0052');assert.throws(()=>validateProvider({...providers[0]},providers));assert.doesNotThrow(()=>validateProvider({...providers[0]},providers,providers[0].name))
})
test('profile URLs reject scripts, credentials and non-YouTube teaser hosts',()=>{
 const p={...marketplaceSeed().providers[0],username:'newacademy'}
 for(const value of ['javascript:alert(1)','https://user:secret@example.com'])assert.throws(()=>validateProvider({...p,socials:{facebook:value}},[]))
 assert.equal(youtubeVideoId('https://youtu.be/YSul9yrAvN4'),'YSul9yrAvN4');assert.equal(youtubeVideoId('https://www.youtube.com/watch?v=YSul9yrAvN4'),'YSul9yrAvN4');assert.equal(youtubeVideoId('https://evil.example/watch?v=YSul9yrAvN4'),'');assert.throws(()=>validateProvider({...p,youtube_url:'https://evil.test/x'},[]))
})
test('one teacher has independent classes and a six-month institute course',()=>{
 const m=marketplaceSeed(),classes=m.classes.filter(c=>c.teacher_account==='TC-SLDA-0001');assert.equal(new Set(classes.map(c=>c.provider)).size,2);assert(classes.some(c=>c.provider==='british-academy'&&c.duration_months===6));assert(m.providers.some(p=>p.owner==='TC-SLDA-0001'&&p.type==='Independent teacher'))
})
test('promotions expire at exactly 30 days; edits cannot extend publication time',()=>{
 const data={news:[{name:'old',published_at:'2026-08-25T00:00:00Z',modified:'2026-09-23T00:00:00Z'},{name:'new',published_at:'2026-08-25T00:00:01Z'}],campaigns:[{name:'old-c',published_at:'2026-08-25T00:00:00Z'}],leads:[{campaign:'old-c'}],invoices:[{name:'never-delete'}]};prunePromotions(data,new Date('2026-09-24T00:00:00Z'));assert.deepEqual(data.news.map(n=>n.name),['new']);assert.equal(data.campaigns.length,0);assert.equal(data.leads.length,1);assert.equal(data.invoices.length,1)
})
test('platform reporting separates accounts, provider profiles and currencies',()=>{
 const d=seed();d.marketplace=marketplaceSeed();const a=platformSummary(d,'year');assert.equal(a.studentCount,360);assert.equal(a.teacherCount,12);assert.equal(a.instituteCount,6);assert.equal(a.independentCount,2);assert.equal(a.buckets.length,12);assert(a.currencies.LKR>0);assert.equal(platformSummary(d,'week').buckets.length,7)
})
