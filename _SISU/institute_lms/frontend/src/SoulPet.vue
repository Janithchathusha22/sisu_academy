<script setup>
import {useId} from 'vue'
defineProps({state:{default:'idle'},paused:Boolean,look:{default:0}})
const id=useId().replaceAll(':','')
</script>
<template><svg class="soul-pet" :class="[state,{paused}]" viewBox="0 0 160 170" fill="none" aria-hidden="true">
<defs><linearGradient :id="id+'body'" x1="45" y1="50" x2="127" y2="150" gradientUnits="userSpaceOnUse"><stop stop-color="#f1e9ff"/><stop offset=".65" stop-color="#c5b2ef"/><stop offset="1" stop-color="#a387d8"/></linearGradient><linearGradient :id="id+'leaf'" x1="65" y1="20" x2="96" y2="41"><stop stop-color="#bee1a2"/><stop offset="1" stop-color="#679e77"/></linearGradient></defs>
<ellipse cx="80" cy="154" rx="35" ry="6" fill="#706092" opacity=".13"/>
<g class="soul-body"><path d="M52 139c-3 8-1 13 9 13h8v-15M95 137v15h9c10 0 12-7 7-14" fill="#9278be"/>
<path d="M44 95c-14-5-22 5-18 17 3 8 12 9 20 4" fill="#c8b7e9" stroke="#9e88c3" stroke-width="2"/>
<g class="soul-hand"><path d="M116 96c10-11 22-5 21 6-1 10-10 17-19 12" fill="#c8b7e9" stroke="#9e88c3" stroke-width="2"/><path d="M126 99l3 4" stroke="#9e88c3" stroke-width="2" stroke-linecap="round"/></g>
<path d="M40 76c0-27 16-40 40-40s40 13 40 40v49c0 19-15 24-40 24s-40-5-40-24z" :fill="`url(#${id}body)`" stroke="#a48ac7" stroke-width="2"/>
<path d="M48 69c0-18 14-25 32-25s32 7 32 25v31c0 17-14 25-32 25s-32-8-32-25z" fill="#fff9ec"/>
<g class="soul-sprout"><path d="M80 41c2-13 1-17-3-23" stroke="#698d68" stroke-width="4" stroke-linecap="round"/><path d="M77 26C57 28 51 18 53 10c16-2 27 5 24 16Z" :fill="`url(#${id}leaf)`"/><path d="M79 32C98 34 108 22 106 13c-18-1-28 9-27 19Z" fill="#91bd86"/><path d="M57 14l18 10m25-6L83 29" stroke="#679574" stroke-width="1.5" stroke-linecap="round"/></g>
<ellipse cx="57" cy="94" rx="8" ry="5" fill="#f5b8b9" opacity=".6"/><ellipse cx="103" cy="94" rx="8" ry="5" fill="#f5b8b9" opacity=".6"/>
<g stroke="#685180" stroke-width="3"><rect x="46" y="68" width="30" height="27" rx="11"/><rect x="84" y="68" width="30" height="27" rx="11"/><path d="M76 78q4-3 8 0m-42-3 4 1m68 0 5-1" stroke-linecap="round"/></g>
<g class="soul-eyes" :style="{transform:`translateX(${look}px)`}"><ellipse cx="63" cy="81" rx="3" ry="5" fill="#514062"/><ellipse cx="97" cy="81" rx="3" ry="5" fill="#514062"/><circle cx="64" cy="79" r="1" fill="white"/><circle cx="98" cy="79" r="1" fill="white"/></g>
<path v-if="state==='thinking'" d="M77 103h6" stroke="#806477" stroke-width="2.5" stroke-linecap="round"/>
<path v-else-if="state==='celebrate'||state==='greeting'" d="M73 101q7 13 14 0Z" fill="#8d6280"/><path v-else d="M75 101q5 5 10 0" stroke="#806477" stroke-width="2.5" stroke-linecap="round"/>
<g class="soul-book"><path d="M58 121q12-4 22 2 10-6 22-2v22q-12-3-22 2-10-5-22-2z" fill="#7563b4" stroke="#5f5194" stroke-width="2"/><path d="M61 123q10-3 19 2 9-5 19-2v16q-10-2-19 3-9-5-19-3z" fill="#f7f1e8"/><path d="M80 125v17" stroke="#ccbde4" stroke-width="2"/><path d="M86 131q9-7 11-2-2 7-10 7Z" fill="#9bc69a"/></g></g></svg></template>
<style scoped>
.soul-pet{width:100%;height:100%;overflow:visible}.soul-body{transform-origin:80px 145px;animation:soul-breathe 4s ease-in-out infinite}.soul-sprout{transform-origin:80px 40px;animation:soul-sway 5s ease-in-out infinite}.soul-eyes{transform-origin:80px 81px;animation:soul-blink 6.4s infinite}.soul-hand{transform-origin:119px 105px}.greeting .soul-hand{animation:soul-wave .55s ease-in-out 4}.celebrate .soul-body{animation:soul-hop .6s ease-in-out 3}.thinking .soul-body{animation:soul-think 1.8s ease-in-out infinite}.thinking .soul-book{animation:soul-page 1.2s ease-in-out infinite;transform-origin:80px 140px}.paused *{animation-play-state:paused!important}@keyframes soul-breathe{50%{transform:translateY(-3px) scale(1.015,1.018)}}@keyframes soul-sway{50%{transform:rotate(8deg)}}@keyframes soul-blink{0%,44%,48%,100%{scale:1 1}46%{scale:1 .12}}@keyframes soul-wave{50%{transform:rotate(-35deg)}}@keyframes soul-hop{50%{transform:translateY(-10px) rotate(-4deg)}}@keyframes soul-think{50%{transform:rotate(3deg) translateY(-2px)}}@keyframes soul-page{50%{transform:rotate(-3deg)}}@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style>
