import {hasStudyPlus} from './timer'
export const palettes=[{id:'lavender',title:'Lavender',color:'#9271c4',dark:'#c9adeb'},{id:'sage',title:'Sage',color:'#6b947d',dark:'#a3c6ac'},{id:'rose',title:'Rose',color:'#b37e91',dark:'#dbabba'},{id:'ocean',title:'Ocean',color:'#688e9f',dark:'#a0c4d2'},{id:'honey',title:'Honey',color:'#ac8855',dark:'#dec18d'}]
export function readAppearance(id,allowPreview=true){let value={};try{value=JSON.parse(localStorage.getItem('sisu-appearance:'+id))||{}}catch{};let plus=false;try{plus=hasStudyPlus(JSON.parse(localStorage.getItem('sisu-study-v1:'+id))?.entitlement)}catch{};return {mode:value.mode==='dark'?'dark':'cozy',accent:allowPreview&&plus&&palettes.some(p=>p.id===value.accent)?value.accent:'lavender',configured:!!value.configured,plus:allowPreview&&plus}}
export function saveAppearance(id,value){localStorage.setItem('sisu-appearance:'+id,JSON.stringify({...value,configured:true}));window.dispatchEvent(new Event('sisu-appearance'))}
export const encouragements=[
 'One small step today is still a step forward.',
 'Your effort matters, even when progress feels quiet.',
 'Someone who cares about you would be proud of your effort.',
 'You deserve rest as much as you deserve progress.',
 'You do not have to understand everything all at once.',
 'Be gentle with yourself. Learning takes time.',
 'A little curiosity can take you somewhere wonderful.',
 'Keep showing up for the future you want, at your own pace.'
]
