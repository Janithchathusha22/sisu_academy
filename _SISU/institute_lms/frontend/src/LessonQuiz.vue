<script setup>
import {ref} from 'vue'
import Icon from './Icon.vue'
import {call} from './service'
const props=defineProps({session:Object})
const emit=defineEmits(['completed'])
const quiz=ref(null),answers=ref([]),result=ref(null),message=ref(''),busy=ref(false)
async function start(){busy.value=true;try{quiz.value=await call('complete_lesson',{session:props.session.name});emit('completed');answers.value=[];result.value=null;message.value=quiz.value?'':'Lesson completed. Your teacher has not added a quiz for this lesson yet.'}catch(e){message.value=e.message}finally{busy.value=false}}
async function submit(){busy.value=true;try{result.value=await call('submit_lesson_quiz',{session:props.session.name,answers:answers.value});message.value=''}catch(e){message.value=e.message}finally{busy.value=false}}
</script>
<template><section class="lesson-quiz"><button v-if="!quiz" class="button subtle small" :disabled="busy" @click="start"><Icon name="ClipboardCheck" :size="16"/>Complete lesson & open quiz</button><p v-if="message" class="field-help" role="status">{{message}}</p><form v-if="quiz&&!result" @submit.prevent="submit"><span class="badge violet">{{quiz.source}}</span><h3>{{quiz.title}}</h3><p v-if="quiz.source==='AI add-on demo'" class="field-help">Illustrative questions only. No AI provider was called and no video transcript was analysed.</p><fieldset v-for="(q,i) in quiz.questions" :key="i"><legend>{{i+1}}. {{q.prompt}}</legend><label v-for="(option,j) in q.options" class="quiz-answer"><input type="radio" :name="session.name+'-question-'+i" v-model.number="answers[i]" :value="j" required>{{option}}</label></fieldset><button class="button primary small" :disabled="busy">Submit answers</button></form><div v-if="result" class="quiz-result" role="status"><Icon name="Award" :size="28"/><div><h3>{{result.score}}% · {{result.correct}} of {{result.total}} correct</h3><p>Your attempt is saved. Keep practising, one lesson at a time.</p></div></div></section></template>
