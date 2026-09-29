export const toolProducts=[
 {id:'todo',title:'My little to-do',price:1,icon:'CheckCheck',description:'Make room for what matters. Plan tasks, set due dates and see them on your LMS calendar.'},
 {id:'journal',title:'A page for me',price:1,icon:'NotebookPen',description:'A quiet place for reflections, small wins and tomorrow’s intentions.'}
]
export function readTools(member){try{const v=JSON.parse(localStorage.getItem('sisu-tools:'+member));return {entitlements:v?.entitlements||{},todos:Array.isArray(v?.todos)?v.todos.slice(0,200):[],journal:Array.isArray(v?.journal)?v.journal.slice(0,200):[]}}catch{return {entitlements:{},todos:[],journal:[]}}}
export function saveTools(member,value){localStorage.setItem('sisu-tools:'+member,JSON.stringify(value));window.dispatchEvent(new Event('sisu-tools'))}
export function toolActive(state,id,now=Date.now()){return Number.isFinite(state.entitlements[id])&&state.entitlements[id]>now}
export function dueTasks(state,date){return state.todos.filter(t=>!t.archived&&t.due===date)}
export function calendarFile(tasks){const esc=s=>String(s).replaceAll('\\','\\\\').replace(/\r\n|\r|\n/g,'\\n').replaceAll(',','\\,').replaceAll(';','\\;');return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Sisu//Study Tasks//EN',...tasks.filter(t=>/^\d{4}-\d{2}-\d{2}$/.test(t.due)&&!t.archived).flatMap(t=>['BEGIN:VEVENT','UID:'+t.id+'@sisu-study','DTSTAMP:'+new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,''),'DTSTART;VALUE=DATE:'+t.due.replaceAll('-',''),'SUMMARY:'+esc(t.title),'TRANSP:TRANSPARENT','END:VEVENT']),'END:VCALENDAR'].join('\r\n')+'\r\n'}
