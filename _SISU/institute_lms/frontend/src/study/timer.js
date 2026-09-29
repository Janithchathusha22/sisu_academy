export const MAX_SESSION_MS=24*60*60*1000
export function createTimer(mode='focus',minutes=25){
 if(!['focus','break','stopwatch'].includes(mode))throw Error('Choose a timer mode')
 if(!Number.isInteger(minutes)||minutes<1||minutes>180)throw Error('Choose 1–180 minutes')
 return {mode,duration:minutes*60000,elapsed:0,startedAt:null,running:false}
}
export function elapsedTime(timer,now=Date.now()){
 const elapsed=timer.elapsed+(timer.running?Math.max(0,now-timer.startedAt):0)
 return Math.min(MAX_SESSION_MS,timer.mode==='stopwatch'?elapsed:Math.min(timer.duration,elapsed))
}
export function displayedTime(timer,now=Date.now()){const elapsed=elapsedTime(timer,now);return timer.mode==='stopwatch'?elapsed:Math.max(0,timer.duration-elapsed)}
export function isFinished(timer,now=Date.now()){return timer.running&&elapsedTime(timer,now)>=(timer.mode==='stopwatch'?MAX_SESSION_MS:timer.duration)}
export function startTimer(timer,now=Date.now()){if(timer.running)return timer;return {...timer,running:true,startedAt:now}}
export function pauseTimer(timer,now=Date.now()){return {...timer,elapsed:elapsedTime(timer,now),running:false,startedAt:null}}
export function formatTimer(ms){const seconds=Math.max(0,Math.ceil(ms/1000));return [Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60].map(n=>String(n).padStart(2,'0')).join(':')}
export function restoreTimer(value){
 if(!value||!['focus','break','stopwatch'].includes(value.mode)||!Number.isFinite(value.duration)||value.duration<60000||value.duration>10800000||!Number.isFinite(value.elapsed)||value.elapsed<0||value.elapsed>MAX_SESSION_MS||typeof value.running!=='boolean'||(value.running&&!Number.isFinite(value.startedAt)))return createTimer()
 return {...value}
}
export const hasStudyPlus=(entitlement,now=Date.now())=>entitlement?.product==='study_plus'&&Number.isFinite(entitlement.expiresAt)&&entitlement.expiresAt>now
