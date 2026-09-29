export const socialNetworks={linkedin:'LinkedIn',youtube:'YouTube',instagram:'Instagram',facebook:'Facebook',twitter:'X / Twitter',tiktok:'TikTok'}
export function providerSocials(kind,value){
 if(!['Teacher','Institute'].includes(kind))return {}
 try{if(typeof value==='string')value=JSON.parse(value)}catch{return {}}
 if(!value||typeof value!=='object'||Array.isArray(value))return {}
 return Object.fromEntries(Object.keys(socialNetworks).flatMap(key=>{try{const url=new URL(value[key]);return url.protocol==='https:'&&!url.username&&!url.password?[[key,url.href]]:[]}catch{return []}}))
}
