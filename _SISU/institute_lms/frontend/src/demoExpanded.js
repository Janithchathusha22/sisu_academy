import { dayKey } from './rules.js'
const shifted = n => dayKey(new Date(Date.now() + n * 86400000))
const pad = (n, digits=5) => String(n).padStart(digits,'0')
export const sampleVideo = 'YSul9yrAvN4'
export const categories = ['Grade 5 Scholarship','O/L','A/L','University','Online Courses']
const teachers = ['Nimal Perera','Kasun Fernando','Dilini Silva','Kavitha Rajan','Fathima Nazeer','Tharindu Samarasinghe','Malithi Dissanayake','Arun Sivarajah','Sajini Wickramasinghe','Rizwan Kareem','Hasini Bandara','Dinesh Wijesinghe']
export const poster = (color, label) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="800" height="400" fill="${color}"/><circle cx="690" cy="90" r="160" fill="white" opacity=".3"/><path d="M580 280l90-180 90 180z" fill="white" opacity=".6"/><text x="36" y="190" font-family="sans-serif" font-size="32" font-weight="700" fill="#242145">${label}</text><text x="38" y="235" font-family="sans-serif" font-size="16" fill="#524b71">SISU LANKA • DEMO ACADEMY</text></svg>`)
export function seed() {
  const specs = [
    ['maths','නිමල් සර්ගේ ගණන් පන්තිය','Combined Mathematics',2,0,'Sinhala',3000],
    ['physics','Physics, made clear.','Physics',2,1,'English',2800],
    ['chemistry','Little reactions. Big discoveries.','Chemistry',2,2,'Sinhala',2800],
    ['economics','Your world, through economics','Economics',2,3,'Tamil',2400],
    ['business','Think like an entrepreneur','Business Studies',2,4,'English',2400],
    ['accounting','Balance your future','Accounting',2,5,'Sinhala',2800],
    ['scholarship-si','පුංචි හපනුන්ගේ පන්තිය','Grade 5 Scholarship',0,6,'Sinhala',1500],
    ['scholarship-ta','சின்னச் சுடர்கள்','Grade 5 Scholarship',0,7,'Tamil',1500],
    ['scholarship-en','Little explorers · Grade 5','Grade 5 Enrichment',0,8,'English',1800],
    ['ol-maths','Step by step, to your A','Mathematics',1,0,'Sinhala',2000],
    ['ol-science','Science for curious minds','Science',1,2,'Sinhala',2000],
    ['ol-english','Find your English voice','English',1,8,'English',1800],
    ['ol-ict','Create. Code. Understand.','ICT',1,9,'English',2000],
    ['ol-tamil','தமிழோடு வளர்வோம்','Tamil',1,7,'Tamil',1800],
    ['uni-writing','Your ideas deserve a voice','Academic Writing',3,10,'English',2500],
    ['uni-stats','Make sense of your data','Research Statistics',3,5,'English',3000],
    ['web-dev','Build your first website','Web Development',4,9,'English',2500],
    ['spoken','Speak with confidence','Spoken English',4,11,'English',2000],
  ]
  const rooms = specs.map(([name,title,subject,c,t,medium,monthly],i)=>({name,title,subject,category:categories[c],medium,teacher:`TC-SLDA-${pad(t+1,4)}`,teacher_name:teachers[t],fee:monthly*6,monthly_fee:monthly,description:`${categories[c]} · ${medium} medium. A six-month programme with weekly lessons, guided practice and friendly teacher feedback. All people and results in this academy are fictional.`,exam_date:c<3?shifted(c===2?76:c===1?140:210):'',motivation:c===0?'පුංචි පියවර, ලොකු හීන':'Make today count.',font:'sans',comments_enabled:1,allow_teacher_access_override:1,active:1,color:['violet','peach','mint'][i%3],tag:categories[c],branch:i%2?'Online campus':'Nugegoda'}))
  const first=['Anuki','Kavindu','Nethmi','Dinuka','Ayesha','Sahan','Tharushi','Isuru','Kavitha','Arun','Fathima','Rizwan','Dulani','Sachith','Shalini','Naveen','Amali','Imran','Yasara','Praveen']
  const last=['Jayasinghe','Perera','Fernando','Silva','Bandara','Rajan','Samarasinghe','Nazeer','Wijesinghe','Kareem','Sivarajah','Dissanayake','Gunawardena','De Silva','Wickramasinghe','Peiris','Hassan','Weerasinghe']
  const students=Array.from({length:360},(_,i)=>{const c=i<100?2:i<210?1:i<300?0:i<330?3:4;return {name:`ST-SLDA-${pad(i+1)}`,user:`student${pad(i+1)}@example.invalid`,full_name:`${first[i%20]} ${last[Math.floor(i/20)]}`,role:'Student',active:1,phone:'',language:['si','ta','en'][i%3],medium:['Sinhala','Tamil','English'][i%3],category:categories[c],grade:c===0?'5':c===1?'11':c===2?'13':'—',stream:c===2?(i%2?'Commerce':'Physical Science'):'General',district:['Colombo','Gampaha','Kandy','Galle','Jaffna','Kurunegala'][i%6],school:c<3?'Demo Central College':'Demo Higher Education Centre',guardian:c<3?`Demo guardian ${pad(i+1)}`:'Not applicable',guardian_contact:'Not supplied · synthetic record',branch:i%2?'Online campus':'Nugegoda',whatsapp_opt_in:0,alias:`Learner ${pad(i+1,3)}`,joined_on:shifted(-180+i%150)}})
  const members=[...students,...teachers.map((full_name,i)=>({name:`TC-SLDA-${pad(i+1,4)}`,user:`teacher${i+1}@example.invalid`,full_name,role:'Teacher',active:1,phone:''})),{name:'AD-SLDA-0001',full_name:'Sanduni Perera',user:'admin@example.invalid',role:'Admin',active:1}]
  const enrollments=[],invoices=[],progress=[]
  students.forEach((s,i)=>{
    const pool=rooms.filter(r=>r.category===s.category)
    const picks=s.category==='A/L'?(i%2?pool.slice(3,6):pool.slice(0,3)):s.category==='Grade 5 Scholarship'?[pool[i%3]]:Array.from({length:2},(_,j)=>pool[(i+j)%pool.length])
    picks.forEach((r,j)=>{
      const name=`ENR-${pad(enrollments.length+1)}`
      enrollments.push({name,classroom:r.name,student:s.name,fee:r.fee,active:1,access_override:'Automatic'})
      for(let month=0;month<6;month++){
        const d=new Date(dayKey()+'T12:00:00');d.setDate(5);d.setMonth(d.getMonth()-5+month)
        const due=dayKey(d),paid=month<5||i===0||(i+j)%5!==0,id=`INV-${pad(invoices.length+1)}`
        invoices.push({name:id,enrollment:name,classroom:r.name,student:s.name,amount:r.monthly_fee,installment:month+1,due_date:due,status:paid?'Paid':due<=dayKey()?'Overdue':'Unpaid',receipt_number:paid?`DEMO-RC-${id}`:'',paid_at:paid?due:''})
      }
      const completed=8+(i*7+j*5)%33,quiz=45+(i*11+j*3)%56,attendance=55+(i*3+j*7)%46
      progress.push({enrollment:name,classroom:r.name,student:s.name,completed,total:40,quiz,attendance,month:dayKey().slice(0,7),monthly_completed:1+(i+j)%8,monthly_total:8})
    })
  })
  rooms.forEach(r=>r.students=enrollments.filter(e=>e.classroom===r.name).length)
  const sessions=rooms.flatMap((r,i)=>[-7,0,7,14].map((offset,j)=>({name:`SESSION-${i}-${j}`,classroom:r.name,title:j===0?'Your classroom · playback demonstration':`${r.subject} · Weekly workshop ${j}`,description:j===0?'Your supplied YouTube stock video demonstrates playback inside the LMS. It is not curriculum content.':'Guided practice, questions and a little progress together.',starts_at:shifted(offset+i%3)+` ${i%2?'18':'16'}:00:00`,ends_at:shifted(offset+i%3)+` ${i%2?'20':'18'}:00:00`,mode:j%2?'Physical':'Online',location:j%2?'Demo Nugegoda · Hall '+(i%3+1):'YouTube classroom',status:j===0?'Completed':'Scheduled',comments:'Inherit',youtube_id:j===0?sampleVideo:''})))
  const campaigns=rooms.slice(0,9).map((r,i)=>({name:`CMP-${i+1}`,classroom:r.name,teacher:r.teacher,headline:i===0?'Your next A starts here.':`${r.subject} · New intake`,description:'Meet your teacher. Try a free introductory class. Find a learning space that feels like yours.',cta_label:'Reserve a free trial',starts_on:shifted(-7),ends_on:shifted(30),status:'Active',channel:['WhatsApp','Facebook','Referral'][i%3],code:`SLDA${i+1}TRIAL`,views:220+i*47,clicks:35+i*8,color:['#e5e0ff','#ffe9d9','#d9f1e8'][i%3]}))
  const leads=campaigns.flatMap((c,i)=>Array.from({length:6+i%4},(_,j)=>({name:`LEAD-${i}-${j}`,campaign:c.name,alias:`Demo enquiry ${i+1}.${j+1}`,status:['New','Contacted','Trial booked','Enrolled'][j%4],source:c.channel,creation:shifted(-j)})))
  return {institute:{name:'SLDA',code:'SLDA',title:'Sisu Lanka Demo Academy',accent:'#7563e6',logo:'',base_fee:15000},members,rooms,enrollments,invoices,progress,sessions,campaigns,leads,
    materials:rooms.map(r=>({name:`MAT-${r.name}`,classroom:r.name,title:'Inside your classroom · video demo',kind:'Recording',youtube_id:sampleVideo,url:`https://youtu.be/${sampleVideo}`,description:'Your supplied stock video. Playback demonstration, not a subject lesson.'})),
    feedback:[{name:'FB-1',classroom:'maths',session:'SESSION-0-0',student:students[0].name,body:'It is helpful to have the recording and class notes in one place.',creation:shifted(-6)}],
    news:[{name:'NEWS-1',headline:'Big dreams start with small steps.',description:'Scholarship, O/L and A/L admissions are open at our fictional demo academy. Find your teacher and try a class.',cta_label:'Explore classrooms',starts_on:shifted(-7),ends_on:shifted(30),images:[{image:poster('#e5e0ff','A fresh start. A bright future.'),alt:'Demo academy admissions'},{image:poster('#d9f1e8','Little learners. Big dreams.'),alt:'Grade 5 demo programme'}]}],
    announcements:rooms.map(r=>({name:`ANN-${r.name}`,classroom:r.name,headline:'Welcome to your learning space',body:'Bring your questions to our next workshop. Your demo teacher is here to help.'})),
    notifications:[{name:'NOTICE-1',student:students[0].name,body:'Your next mathematics workshop is ready on your timetable.',status:'Queued',creation:shifted(0)}],audits:[]}
}
