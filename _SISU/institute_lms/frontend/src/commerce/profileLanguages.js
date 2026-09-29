import catalog from './languageCatalog.json'
import {locales} from '../locales.js'

const overrides={ar:'العربية',zh:'中文',si:'සිංහල',ta:'தமிழ்'}
const known=new Map(locales.filter(r=>!r.code.includes('-')).map(r=>[r.code,r.native]))
export const profileLanguages=catalog.map(([code,label,aliases])=>{
  let native=overrides[code]||known.get(code)||''
  if(!native&&code.length===2){try{native=new Intl.DisplayNames([code],{type:'language',fallback:'none'}).of(code)||''}catch{}}
  return {code,label,aliases,native}
})
const fold=value=>value.normalize('NFKC').toLocaleLowerCase().trim()
export function searchLanguages(query){
  const q=fold(query)
  if(!q)return profileLanguages
  const matches=profileLanguages.filter(r=>fold(`${r.code} ${r.label} ${r.aliases} ${r.native}`).includes(q))
  return matches.sort((a,b)=>Number(fold(b.code)===q||fold(b.label)===q||fold(b.native)===q)-Number(fold(a.code)===q||fold(a.label)===q||fold(a.native)===q))
}
