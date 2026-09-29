<script setup>
import {ref} from 'vue'
import {request} from './client'
const phone=ref(''),code=ref(''),sent=ref(false),verified=ref(false),error=ref(''),busy=ref(false)
async function run(method,args){error.value='';busy.value=true;try{await request('mobile_verification',method,args);if(method==='verify')verified.value=true;else sent.value=true}catch(e){error.value=e.message}finally{busy.value=false}}
</script>
<template><section class="panel mobile-onboarding"><h2>A number that belongs to you.</h2><p>Verify your mobile before submitting your profile.</p><p v-if="error" role="alert">{{error}}</p><p v-if="verified" role="status">Mobile verified. You can now save your profile.</p><template v-else><form @submit.prevent="run('request_code',{phone})"><label>Mobile number<input v-model="phone" type="tel" required pattern="\+[1-9][0-9]{7,14}" placeholder="+94…"></label><button class="button subtle" :disabled="busy">{{sent?'Send a new code':'Send verification code'}}</button></form><form v-if="sent" @submit.prevent="run('verify',{code})"><label>Six-digit code<input v-model="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required></label><button class="button primary" :disabled="busy">Verify number</button></form></template></section></template>
<style>.mobile-onboarding{padding:25px;margin:25px 0}.mobile-onboarding p{margin:15px 0;font-size:13px}.mobile-onboarding label{display:flex;flex-direction:column;gap:10px;margin:20px 0;font-size:12px}.mobile-onboarding input{padding:14px;border:1px solid #ddcde9;border-radius:12px}</style>
