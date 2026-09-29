<script setup>
import {computed, ref} from 'vue'
import {educationLevels, searchEducation} from './educationLevels.js'
const props=defineProps({modelValue:{type:String,default:''}})
const emit=defineEmits(['update:modelValue'])
const query=ref(''),category=ref(''),message=ref('')
const selected=computed(()=>String(props.modelValue||'').split(',').map(s=>s.trim()).filter(Boolean))
const categories=[...new Set(educationLevels.map(row=>row.category))]
const results=computed(()=>searchEducation(query.value,category.value))
const custom=computed(()=>query.value.replace(/,/g,' ').trim().replace(/\s+/g,' '))
const isSelected=label=>selected.value.some(s=>s.toLocaleLowerCase()===label.toLocaleLowerCase())
const canCustom=computed(()=>custom.value&&!educationLevels.some(row=>row.label.toLocaleLowerCase()===custom.value.toLocaleLowerCase())&&!isSelected(custom.value))
function toggle(label){
  message.value=''
  const next=isSelected(label)?selected.value.filter(s=>s.toLocaleLowerCase()!==label.toLocaleLowerCase()):[...selected.value,label]
  if(next.join(', ').length>150){message.value='Your selections are too long. Remove a level or use a shorter custom name.';return}
  emit('update:modelValue',next.join(', '))
}
function addCustom(){if(canCustom.value){toggle(custom.value);if(!message.value)query.value=''}}
</script>
<template>
  <fieldset class="education-picker">
    <legend>Grades / course levels</legend>
    <p class="education-intro">Find your learning stage, school year or qualification. Choose one or more.</p>
    <div v-if="selected.length" class="education-selected" aria-label="Selected education levels">
      <button v-for="level in selected" :key="level" type="button" :aria-label="`Remove ${level}`" @click="toggle(level)">{{level}} <span aria-hidden="true">×</span></button>
    </div>
    <div class="education-filters">
      <label>Search education levels<input v-model="query" type="search" maxlength="100" placeholder="Try Grade 7, A/L, IB, diploma…" @keydown.enter.prevent="addCustom"></label>
      <label>Education category<select v-model="category"><option value="">All education</option><option v-for="name in categories" :key="name">{{name}}</option></select></label>
    </div>
    <small aria-live="polite">{{results.length}} options · {{selected.length}} selected</small>
    <div class="education-results" role="group" aria-label="Available education levels" tabindex="0">
      <label v-for="row in results" :key="row.label" class="education-option">
        <input type="checkbox" :checked="isSelected(row.label)" @change="toggle(row.label)">
        <span>{{row.label}}<small>{{row.category}}</small></span>
      </label>
      <p v-if="!results.length">No matching options. Try another search or add your local qualification below.</p>
    </div>
    <button v-if="canCustom" type="button" class="button subtle small education-custom" @click="addCustom">+ Add “{{custom}}”</button>
    <p class="education-note">Not listed? Type the name to add it. Local systems vary; these options do not imply equivalent qualifications.</p>
    <p v-if="message" role="alert">{{message}}</p>
  </fieldset>
</template>
<style scoped>
.education-picker{min-width:0;margin:24px 0;padding:20px;border:1px solid var(--student-border);border-radius:18px;background:var(--student-card);color:var(--student-ink)}
.education-picker legend{padding:0 8px;font-size:13px;font-weight:600}.education-picker .education-intro{margin:0 0 14px;font-size:12px;line-height:1.7}
.education-filters{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:12px}.education-picker .education-filters label{margin:8px 0 14px;min-width:0}.education-filters input,.education-filters select{width:100%;min-width:0;box-sizing:border-box;font:inherit;padding:12px;border:1px solid var(--student-border);border-radius:12px;background:var(--student-card);color:var(--student-ink)}
.education-picker small{display:block;color:var(--student-muted);font-size:11px;line-height:1.6}.education-selected{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.education-selected button{border:1px solid var(--student-border);background:var(--student-soft,#ede5f8);color:var(--student-ink);border-radius:20px;padding:8px 12px;text-align:start;font-size:12px;overflow-wrap:anywhere}.education-selected span{padding-inline-start:6px}
.education-results{max-height:235px;overflow-y:auto;overscroll-behavior:contain;margin-top:10px;border:1px solid var(--student-border);border-radius:12px;padding:4px 12px}.education-picker .education-option{display:flex;flex-direction:row;align-items:center;gap:12px;margin:0;padding:10px 2px;border-bottom:1px solid var(--student-border);cursor:pointer;line-height:1.6}.education-option:last-child{border:0}.education-option input{width:17px;height:17px;flex:0 0 auto;accent-color:#8e70ba}.education-option span{min-width:0}.education-picker .education-note{font-size:11px;line-height:1.7;margin-bottom:0;color:var(--student-muted)}.education-custom{margin-top:12px;max-width:100%;white-space:normal;overflow-wrap:anywhere}
@media(max-width:600px){.education-filters{grid-template-columns:1fr;gap:0}.education-picker{padding:14px}}
</style>
