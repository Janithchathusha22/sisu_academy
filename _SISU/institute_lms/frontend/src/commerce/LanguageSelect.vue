<script setup>
import {computed,ref,watch} from 'vue'
import {profileLanguages,searchLanguages} from './profileLanguages.js'
const props=defineProps({modelValue:{type:String,default:''}})
const emit=defineEmits(['update:modelValue'])
const query=ref(''),limit=ref(40),message=ref('')
const selected=computed(()=>String(props.modelValue||'').split(',').map(s=>s.trim()).filter(Boolean))
const results=computed(()=>searchLanguages(query.value))
const custom=computed(()=>query.value.replace(/,/g,' · ').trim().replace(/\s+/g,' '))
const same=(a,b)=>a.normalize('NFKC').toLocaleLowerCase()===b.normalize('NFKC').toLocaleLowerCase()
const isSelected=label=>selected.value.some(s=>same(s,label))
const canCustom=computed(()=>custom.value&&!profileLanguages.some(r=>[r.label,r.code,r.native,...r.aliases.split('; ')].some(name=>same(name,custom.value)))&&!isSelected(custom.value))
watch(query,()=>{limit.value=40;message.value=''})
function toggle(label){
  message.value=''
  const next=isSelected(label)?selected.value.filter(s=>!same(s,label)):[...selected.value,label]
  if(next.join(', ').length>150){message.value='Your language list is too long. Remove a selection or shorten a custom name.';return}
  emit('update:modelValue',next.join(', '))
}
function addCustom(){if(canCustom.value){toggle(custom.value);if(!message.value)query.value=''}}
</script>
<template>
  <fieldset class="profile-language-picker">
    <legend>Languages</legend>
    <p>Choose the languages you speak, learn or teach.</p>
    <div v-if="selected.length" class="profile-language-selected" aria-label="Selected profile languages">
      <button v-for="name in selected" :key="name" type="button" :aria-label="`Remove language ${name}`" @click="toggle(name)"><bdi>{{name}}</bdi> <span aria-hidden="true">×</span></button>
    </div>
    <label>Search languages<input v-model="query" type="search" maxlength="100" placeholder="Search English, සිංහල, தமிழ், العربية…" @keydown.enter.prevent="addCustom"></label>
    <small aria-live="polite">{{results.length.toLocaleString()}} {{results.length===1?'option':'options'}} · {{selected.length}} selected</small>
    <div class="profile-language-results" role="group" aria-label="Available profile languages" tabindex="0">
      <label v-for="row in results.slice(0,limit)" :key="row.code" class="profile-language-option"><input type="checkbox" :checked="isSelected(row.label)" @change="toggle(row.label)"><span><bdi>{{row.label}}</bdi><small><bdi v-if="row.native">{{row.native}} · </bdi>{{row.code}}</small></span></label>
      <p v-if="!results.length">No matching languages. You can add a language or dialect below.</p>
    </div>
    <button v-if="results.length>limit" type="button" class="button subtle small profile-language-more" @click="limit+=40">Show more languages</button>
    <button v-if="canCustom" type="button" class="button subtle small profile-language-more" @click="addCustom">+ Add “{{custom}}”</button>
    <p class="profile-language-help">Search by language name, native name where available, or language code. You can also add your own language or dialect.</p>
    <p v-if="message" role="alert">{{message}}</p>
  </fieldset>
</template>
<style scoped>
.profile-language-picker{min-width:0;margin:24px 0;padding:20px;border:1px solid var(--student-border);border-radius:18px;background:var(--student-card);color:var(--student-ink)}.profile-language-picker legend{padding:0 8px;font-size:13px;font-weight:600}.profile-language-picker p{font-size:12px;line-height:1.7;margin:0 0 14px}.profile-language-picker label{font-size:12px}.profile-language-picker input[type=search]{width:100%;box-sizing:border-box;min-width:0}.profile-language-picker small{display:block;color:var(--student-muted);font-size:11px;line-height:1.7}
.profile-language-selected{display:flex;gap:8px;flex-wrap:wrap}.profile-language-selected button{border:1px solid var(--student-border);background:var(--student-soft,#ede5f8);color:var(--student-ink);border-radius:20px;padding:8px 12px;text-align:start;font-size:12px;overflow-wrap:anywhere}.profile-language-selected span{padding-inline-start:6px}.profile-language-results{max-height:235px;overflow-y:auto;overscroll-behavior:contain;border:1px solid var(--student-border);border-radius:12px;margin-top:10px;padding:4px 12px}
.profile-language-picker .profile-language-option{display:flex;flex-direction:row;gap:12px;align-items:center;margin:0;padding:10px 2px;border-bottom:1px solid var(--student-border);cursor:pointer;line-height:1.6}.profile-language-option:last-child{border:0}.profile-language-option input{width:17px;height:17px;flex:0 0 auto;accent-color:#8e70ba}.profile-language-option span{min-width:0}.profile-language-more{margin-top:12px;max-width:100%;white-space:normal;overflow-wrap:anywhere}.profile-language-picker .profile-language-help{font-size:11px;color:var(--student-muted);margin:12px 0 0}@media(max-width:600px){.profile-language-picker{padding:14px}}
</style>
