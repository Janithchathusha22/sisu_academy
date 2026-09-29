import {demoScale} from './grades.js'
export function parseCsv(text){
 const rows=[];let row=[],cell='',quoted=false
 for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++}else quoted=!quoted}else if(c===','&&!quoted){row.push(cell);cell=''}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(v=>v.trim()))rows.push(row);row=[];cell=''}else cell+=c}
 if(quoted)throw Error('The CSV contains an unclosed quoted cell.')
 row.push(cell);if(row.some(v=>v.trim()))rows.push(row);return rows
}
export function tableRecords(table){
 if(table.length<2)throw Error('Add a header and at least one result row.')
 const headings=table[0].map(c=>String(c).replace(/^\uFEFF/,'').trim().toLowerCase().replace(/[\s-]+/g,'_'))
 const student=headings.findIndex(c=>['student_id','student','id'].includes(c)),grade=headings.indexOf('grade'),credits=headings.indexOf('credits')
 if(student<0||grade<0)throw Error('Required columns: Student ID and Grade. Credits is optional.')
 if(table.length>1001)throw Error('Import at most 1,000 results at a time.')
 return table.slice(1).filter(r=>r.some(c=>String(c).trim())).map((r,i)=>({line:i+2,student:String(r[student]||'').trim(),grade:String(r[grade]||'').trim().toUpperCase(),credits:credits<0||r[credits]===''?null:Number(r[credits])}))
}
export function validateResults(rows,enrollments,defaults){
 const ids=new Set(enrollments.filter(e=>e.classroom===defaults.classroom&&e.active!==0).map(e=>e.student)),seen=new Set()
 return rows.map(row=>{const credits=row.credits??Number(defaults.credits),errors=[];if(!ids.has(row.student))errors.push('Student is not enrolled in this class');if(seen.has(row.student))errors.push('Duplicate student in this file');seen.add(row.student);if(!Object.hasOwn(demoScale,row.grade))errors.push('Unknown grade');if(!Number.isFinite(credits)||credits<=0||credits>60)errors.push('Credits must be greater than 0 and at most 60');return {...row,credits,classroom:defaults.classroom,term:defaults.term.trim(),excluded:false,errors}})
}
export function pdfTextRows(items){
 const lines=[]
 for(const item of items){if(!item.str?.trim())continue;const y=item.transform[5];let line=lines.find(l=>Math.abs(l.y-y)<3);if(!line){line={y,items:[]};lines.push(line)}line.items.push(item)}
 return lines.sort((a,b)=>b.y-a.y).map(line=>line.items.sort((a,b)=>a.transform[4]-b.transform[4]).map(i=>i.str).join(' ').trim())
}
export function pdfRecords(lines){
 // Deliberately strict, documented table layout: Student ID | Grade | Credits.
 const rows=[],unmatched=[]
 for(const [i,line] of lines.entries()){if(!/ST-[A-Z0-9]+-\d+/i.test(line))continue;const match=line.match(/^\s*(ST-[A-Z0-9]+-\d+)\s+([A-F][+-]?)(?:\s+(\d+(?:\.\d+)?))?\s*$/i);if(!match){unmatched.push(i+1);continue}rows.push({line:i+1,student:match[1].toUpperCase(),grade:match[2].toUpperCase(),credits:match[3]===undefined?null:Number(match[3])})}
 if(unmatched.length)throw Error('PDF rows '+unmatched.slice(0,8).join(', ')+' could not be read safely. Use the table format Student ID, Grade, Credits or upload Excel.')
 if(!rows.length)throw Error('No readable result table found. Scanned PDFs need OCR. Use a text PDF with Student ID, Grade, Credits columns, or upload Excel.')
 if(rows.length>1000)throw Error('Import at most 1,000 results at a time.');return rows
}
export function checkXlsxSize(buffer){
 const d=new DataView(buffer);let end=-1
 for(let i=d.byteLength-22;i>=Math.max(0,d.byteLength-65557);i--)if(d.getUint32(i,true)===0x06054b50){end=i;break}
 if(end<0)throw Error('This is not a valid XLSX workbook.')
 const count=d.getUint16(end+10,true);let pos=d.getUint32(end+16,true),total=0
 if(count>1500)throw Error('Workbook is too complex. Save a results-only workbook.')
 for(let i=0;i<count;i++){if(pos+46>d.byteLength||d.getUint32(pos,true)!==0x02014b50)throw Error('Invalid workbook archive.');total+=d.getUint32(pos+24,true);if(total>30*1024*1024)throw Error('Expanded workbook exceeds 30 MB. Use a results-only workbook.');pos+=46+d.getUint16(pos+28,true)+d.getUint16(pos+30,true)+d.getUint16(pos+32,true)}
}
export async function readResultFile(file){
 if(file.size>5*1024*1024)throw Error('Choose a file under 5 MB.')
 const suffix=file.name.split('.').at(-1).toLowerCase()
 if(suffix==='csv')return {rows:tableRecords(parseCsv(await file.text())),note:'CSV data · review before publishing'}
 const buffer=await file.arrayBuffer()
 if(suffix==='xlsx'){
  checkXlsxSize(buffer);const {readSheet}=await import('read-excel-file/browser');const rows=await readSheet(file)
  if(rows.length>1001||rows.some(r=>r.length>30))throw Error('Use the first worksheet, with at most 1,000 results and 30 columns.')
  return {rows:tableRecords(rows.map(r=>r.map(v=>v??''))),note:'First worksheet imported. Formulas are not calculated; review the values against your source.'}
 }
 if(suffix==='pdf'){
  const pdf=await import('pdfjs-dist');pdf.GlobalWorkerOptions.workerSrc=(await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default
  const task=pdf.getDocument({data:new Uint8Array(buffer),isEvalSupported:false,useSystemFonts:false,stopAtErrors:true})
  task.onPassword=()=>task.destroy()
  try{const document=await task.promise;if(document.numPages>20)throw Error('Use a PDF of at most 20 pages.');let lines=[];for(let i=1;i<=document.numPages;i++){const page=await document.getPage(i);const content=await page.getTextContent();lines.push(...pdfTextRows(content.items));page.cleanup()}return {rows:pdfRecords(lines),note:'Text extracted from '+document.numPages+' PDF page(s). Compare every row with your original document.'}}finally{await task.destroy()}
 }
 throw Error('Use .xlsx, .csv or a text-based .pdf file. Legacy .xls files must be saved as .xlsx.')
}
