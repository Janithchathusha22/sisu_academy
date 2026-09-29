import {regions,menaCountries} from './regions.js'
import {keywords} from './discoveryRanking.js'
export const educationPresets = {
  'Sri Lanka':['National curriculum · Grade 5 / O/L / A/L','Cambridge International','University / Higher education','Professional / Short courses'],
  'United Kingdom':['National curriculum · GCSE / A level','Cambridge International','University / Higher education','Professional / Short courses'],
  'India':['CBSE','ICSE / ISC','State curriculum','University / Higher education','Professional / Short courses'],
  'United States':['K–12 / AP','State curriculum','University / Higher education','Professional / Short courses'],
  'Australia':['Australian curriculum','State senior secondary','University / Higher education','Professional / Short courses'],
  'Other':['National curriculum','Cambridge International','International Baccalaureate','University / Higher education','Professional / Short courses','Custom education system']
}
for(const country of menaCountries)educationPresets[country]=[country+' national curriculum','British curriculum · GCSE / A level','American curriculum · K–12 / AP','International Baccalaureate','Cambridge International','University / Higher education','Diploma / HND','Professional / Short courses','Custom education system']
export function youtubeVideoId(url){
  if(!url)return ''
  try{const u=new URL(url);if(u.protocol!=='https:'||u.username||u.password)return '';let id='';if(u.hostname==='youtu.be')id=u.pathname.slice(1);else if(['youtube.com','www.youtube.com','m.youtube.com'].includes(u.hostname))id=u.pathname==='/watch'?u.searchParams.get('v'):u.pathname.match(/^\/(?:embed|live|shorts)\/([^/]+)$/)?.[1];return /^[\w-]{11}$/.test(id||'')?id:''}catch{return ''}
}
export function validateProvider(v, existing, exclude=null){
  if(!['Institute','Independent teacher'].includes(v.type))throw Error('Choose institute or independent teacher')
  if(!v.title?.trim()||v.title.length>100)throw Error('Add a name of up to 100 characters')
  if(!/^[a-z][a-z0-9]{2,29}$/.test(v.username||''))throw Error('Username: 3–30 lowercase letters and numbers, starting with a letter')
  if(existing.some(p=>p.username===v.username&&p.name!==exclude))throw Error('This public username is already taken')
  if(!v.country?.trim()||!v.education_system?.trim()||!v.languages?.trim())throw Error('Country, education system and teaching languages are required')
  if((v.bio||'').length>1000)throw Error('Keep the profile description within 1,000 characters')
  if(v.type==='Independent teacher'&&(!v.subjects?.trim()||!v.qualifications?.trim()))throw Error('Add teaching subjects and qualifications')
  if(v.timezone){try{new Intl.DateTimeFormat('en',{timeZone:v.timezone}).format()}catch{throw Error('Choose a valid IANA time zone')}}
  const tags=keywords(v.keywords||[],v.type==='Institute'?15:5);if(!tags.length)throw Error('Add at least one keyword so learners can discover your profile')
  if(v.currency&&!/^[A-Z]{3}$/.test(v.currency))throw Error('Use a three-letter currency code')
  if(v.country==='Other'&&!v.custom_country?.trim())throw Error('Enter your country name')
  if(v.education_system==='Custom education system'&&!v.custom_system?.trim())throw Error('Enter your education system name')
  if(v.youtube_url&&!youtubeVideoId(v.youtube_url))throw Error('Enter a valid HTTPS YouTube video URL')
  if(!['Public','Unlisted','Private'].includes(v.video_visibility||'Public'))throw Error('Choose a valid YouTube visibility label')
  if(v.experience!==undefined&&(!Number.isInteger(Number(v.experience))||Number(v.experience)<0||Number(v.experience)>80))throw Error('Teaching experience must be between 0 and 80 years')
  for(const link of Object.values(v.socials||{})){if(!link)continue;try{const u=new URL(link);if(u.protocol!=='https:'||u.username||u.password)throw Error()}catch{throw Error('Public social links must be HTTPS URLs without embedded credentials')}}
  if(v.website){try{const u=new URL(v.website);if(u.protocol!=='https:'||u.username||u.password)throw Error()}catch{throw Error('Website links must begin with https://')}}
}
export function nextProviderCode(title, existing){
  const prefix=title.trim().split(/\s+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('').toUpperCase().replace(/[^A-Z]/g,'')||'ED'
  let n=51;while(existing.some(p=>p.code===prefix+String(n).padStart(4,'0')))n++
  return prefix+String(n).padStart(4,'0')
}
export function marketplaceSeed(){
 const providers=[
 {name:'teen-academy',type:'Institute',title:'Teen Academy Sri Lanka',username:'teenacademysl',code:'TA0051',country:'Sri Lanka',city:'Colombo',education_system:'National curriculum · Grade 5 / O/L / A/L',languages:'Sinhala, Tamil, English',bio:'A fictional tuition academy bringing scholarship, O/L and A/L learners together. Small steps, supportive teachers and a clear plan for each exam.',subjects:'Mathematics, Science, English',color:'#e6def9',symbol:'TA',owner:null},
 {name:'northbridge',type:'Institute',title:'Northbridge Learning',username:'northbridgeuk',code:'NL0051',country:'United Kingdom',city:'Manchester',education_system:'National curriculum · GCSE / A level',languages:'English',bio:'A fictional learning centre for GCSE and A-level students. Weekly tutorials, revision workshops and space to ask every question.',subjects:'GCSE Mathematics, A-level Physics',color:'#ddecf8',symbol:'NL',owner:null},
 {name:'lotus-learning',type:'Institute',title:'Lotus Learning Centre',username:'lotuslearningin',code:'LL0051',country:'India',city:'Bengaluru',education_system:'CBSE',languages:'English, Hindi',bio:'A fictional CBSE learning community with structured practice, live classes and friendly feedback for school learners.',subjects:'Mathematics, Science',color:'#fae5d5',symbol:'LL',owner:null},
 {name:'nimal-teacher',type:'Independent teacher',title:'Nimal Perera',username:'nimalmaths',code:'NP0051',country:'Sri Lanka',city:'Nugegoda',education_system:'National curriculum · Grade 5 / O/L / A/L',languages:'Sinhala, English',bio:'I help learners turn difficult mathematics into manageable steps. My fictional teaching profile includes weekly paper discussions, worked examples and guided revision.',subjects:'Combined Mathematics, O/L Mathematics',qualifications:'BSc in Mathematics · demonstration credential',experience:12,teaching_style:'Worked examples, weekly practice and small-group feedback',availability:'Tuesday & Saturday · 16:00–18:00 Asia/Colombo',color:'#e5defa',symbol:'NP',owner:'TC-SLDA-0001',website:''},
 {name:'maya-teacher',type:'Independent teacher',title:'Maya Wilson',username:'mayascience',code:'MW0051',country:'United Kingdom',city:'Bristol',education_system:'Cambridge International',languages:'English',bio:'A fictional science teacher making big ideas feel approachable. Learn through examples, experiments and curious questions.',subjects:'IGCSE Biology, IGCSE Chemistry',qualifications:'MSc in Science Education · demonstration credential',experience:8,teaching_style:'Visual explanations, practice questions and discussion',availability:'Saturday · 10:00–12:00 Europe/London',color:'#dceee6',symbol:'MW',owner:null,website:''}
 ]
 providers.push({name:'british-academy',type:'Institute',title:'British Academy · Demo',username:'britishacademydemo',code:'BA0051',country:'Sri Lanka',city:'Colombo',education_system:'Professional / Short courses',languages:'English, Sinhala',bio:'A fictional academy running six-month enrichment courses. Teachers may also run their own independent classes or teach at other institutes.',subjects:'AI for Kids, Digital Literacy',color:'#dae7f9',symbol:'BA',owner:null})
 providers.push({name:'noor-academy',type:'Institute',title:'أكاديمية نور · Noor Academy',username:'nooracademyuae',code:'NA0051',country:'United Arab Emirates',city:'Dubai',education_system:'United Arab Emirates national curriculum',languages:'Arabic, English',bio:'A fictional bilingual academy for learners in the UAE. National and international pathways, live classes and support in Arabic and English.',subjects:'Mathematics, Science, Digital Literacy',color:'#deeee8',symbol:'NA',owner:null})
 const classes=[
 ['na-maths','noor-academy','الرياضيات بثقة · Maths with confidence','Grade 9','Arabic',180,'AED','Layla Hassan'],
 ['na-science','noor-academy','Science explorers · British curriculum','IGCSE','English',220,'AED','Layla Hassan'],
 ['ba-ai-kids','british-academy','AI for Kids · A six-month discovery course','Enrichment · Ages 10–14','English',2500,'LKR','Nimal Perera'],
 ['ta-scholarship','teen-academy','පුංචි හපනුන් · Grade 5','Grade 5 Scholarship','Sinhala',1500,'LKR','Malithi Dissanayake'],
 ['ta-ol','teen-academy','Your next A · O/L Mathematics','O/L','Sinhala',2000,'LKR','Nimal Perera'],
 ['ta-al','teen-academy','A/L Combined Mathematics','A/L','English',3000,'LKR','Nimal Perera'],
 ['nb-gcse','northbridge','GCSE Maths · Build your confidence','GCSE','English',35,'GBP','Oliver Reed'],
 ['nb-al','northbridge','A-level Physics · Understand the why','A level','English',45,'GBP','Emma Clarke'],
 ['ll-10','lotus-learning','CBSE Class 10 · Maths made clear','Class 10','English',1800,'INR','Ananya Rao'],
 ['ll-12','lotus-learning','CBSE Class 12 · Science workshop','Class 12','Hindi',2200,'INR','Arjun Mehta'],
 ['np-al','nimal-teacher','නිමල් සර්ගේ ගණන් පන්තිය','A/L','Sinhala',3000,'LKR','Nimal Perera'],
 ['np-ol','nimal-teacher','O/L Maths · A fresh start','O/L','English',2000,'LKR','Nimal Perera'],
 ['mw-bio','maya-teacher','IGCSE Biology · Living science','IGCSE','English',30,'GBP','Maya Wilson'],
 ['mw-chem','maya-teacher','IGCSE Chemistry · Curious reactions','IGCSE','English',30,'GBP','Maya Wilson']
 ].map(([name,provider,title,level,medium,fee,currency,teacher])=>({name,provider,title,level,medium,fee,currency,teacher,mode:'Online',description:'A fictional monthly class with weekly live lessons, practice materials and teacher feedback. The sample recording demonstrates YouTube playback.',youtube_id:'YSul9yrAvN4'}))
 classes.forEach(c=>{if(c.provider==='nimal-teacher'||c.provider==='british-academy')c.teacher_account='TC-SLDA-0001';if(c.provider==='british-academy'){c.duration_months=6;c.schedule='Saturday · 10:00–11:30 · Asia/Colombo';c.description='Six-month fictional enrichment course about responsible AI and digital literacy. Monthly tuition is billed by British Academy. This course topic is separate from the optional AI Quiz product add-on.'}})
 providers.forEach(p=>{const region=regions[p.country];p.currency=region?.currency||'USD';p.timezone=region?.timezone||'UTC';p.youtube_url=p.type==='Independent teacher'?'https://youtu.be/YSul9yrAvN4':'';p.video_visibility='Public';p.socials={};p.keywords=keywords(p.subjects||'education',p.type==='Institute'?15:5)})
 classes.forEach((c,i)=>{c.keywords=keywords([c.level,...(providers.find(p=>p.name===c.provider)?.keywords||[])],20);c.active_learners_30d=35+(i*47)%230})
 return {providers,classes,enrollments:[]}
}
