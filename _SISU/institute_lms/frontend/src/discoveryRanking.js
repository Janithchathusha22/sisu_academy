const aliases={maths:'mathematics',math:'mathematics',it:'computing',ict:'computing'}
export const normalizeKeyword=value=>{const n=String(value).normalize('NFKC').trim().toLocaleLowerCase().replace(/\s+/g,' ');return aliases[n]||n}
export function keywords(value,limit){
 const list=Array.isArray(value)?value:String(value||'').split(/[,;\n]/)
 const cleaned=[...new Set(list.map(normalizeKeyword).filter(Boolean))]
 if(cleaned.length>limit)throw Error(`Use at most ${limit} keywords.`)
 if(cleaned.some(k=>[...k].length>40))throw Error('Keep each keyword within 40 characters.')
 return cleaned
}
export function rankDiscovery(providers,classes,interests=[],engaged=[],mode='Suggested'){
 const wanted=keywords(interests,20),history=keywords(engaged,100),max=Math.max(1,...providers.map(p=>classes.filter(c=>c.provider===p.name).reduce((s,c)=>s+(c.active_learners_30d||0),0)))
 return providers.map(p=>{
  const offered=keywords([...(p.keywords||[]),...classes.filter(c=>c.provider===p.name).flatMap(c=>c.keywords||[])],100)
  const matches=wanted.filter(k=>offered.some(t=>t===k||t.includes(k)||k.includes(t)))
  const related=history.filter(k=>offered.some(t=>t===k||t.includes(k)||k.includes(t)))
  const activity=classes.filter(c=>c.provider===p.name).reduce((s,c)=>s+(c.active_learners_30d||0),0)
  const popularity=Math.log1p(activity)/Math.log1p(max)
  const score=mode==='Most active'?activity:40*(matches.length/Math.max(1,wanted.length))+20*(related.length/Math.max(1,history.length))+40*popularity
  return {...p,discovery:{score,activity,matches,reason:matches.length?'Matches '+matches.slice(0,2).join(' & '):related.length?'Related to classes you joined':activity?'Popular with learners':'New learning community'}}
 }).sort((a,b)=>b.discovery.score-a.discovery.score||a.title.localeCompare(b.title))
}
