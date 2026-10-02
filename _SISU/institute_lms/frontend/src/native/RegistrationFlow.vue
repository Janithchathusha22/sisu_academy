<script setup>
import {ref} from 'vue'
import {signInWithGoogle,signUp} from '../lib/supabase'
import {currentSession} from '../lib/api'

const emit=defineEmits(['back','authenticated'])
const type=ref('student'),busy=ref(false),error=ref(''),done=ref(false)
const form=ref({full_name:'',email:'',password:'',organization:'',subject:'',country:'',timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})

async function submit(){
  busy.value=true;error.value=''
  try{
    const data=await signUp({email:form.value.email,password:form.value.password,fullName:form.value.full_name,
      accountType:type.value,details:{organization:form.value.organization,subject:form.value.subject,country:form.value.country,timezone:form.value.timezone}})
    if(data.session)emit('authenticated',await currentSession())
    else done.value=true
  }catch(e){error.value=e.message}finally{busy.value=false}
}
async function google(){try{await signInWithGoogle()}catch(e){error.value=e.message}}
</script>

<template>
  <main class="application-shell"><header><strong>sisu ✦</strong><button @click="emit('back')">← Back to sign in</button></header>
    <div class="application-layout"><aside><span class="eyebrow">A PLACE FOR YOUR NEXT CHAPTER</span><h1>Good people.<br>Bright futures.<br><em>One little space.</em></h1><p>Supabase-secured learning, teaching and community.</p><div class="application-art">✦ <span>❀</span> ✧</div></aside>
      <section class="panel application-form"><p v-if="error" class="error" role="alert">{{error}}</p>
        <template v-if="done"><h2>Check your email</h2><p>Use the confirmation link sent by Supabase, then return here and sign in. Teacher and institute applications remain pending until an administrator approves them.</p><button class="button primary" @click="emit('back')">Back to sign in</button></template>
        <form v-else @submit.prevent="submit"><span class="eyebrow">CREATE A SECURE ACCOUNT</span><h2>Start your Sisu space.</h2>
          <div class="account-types"><button v-for="row in [{id:'student',label:'Student'},{id:'teacher',label:'Teacher'},{id:'institute',label:'Institute'}]" :key="row.id" type="button" :class="{active:type===row.id}" @click="type=row.id">{{row.label}}</button></div>
          <p v-if="type!=='student'" class="application-policy">Provider accounts are created as pending. Choosing a role here never grants privileged access.</p>
          <label>Full name<input v-model="form.full_name" autocomplete="name" required maxlength="120"></label>
          <label>Email<input v-model="form.email" type="email" autocomplete="email" required maxlength="254"></label>
          <label>Password<input v-model="form.password" type="password" autocomplete="new-password" required minlength="8" maxlength="72"></label>
          <label v-if="type==='institute'">Institute name<input v-model="form.organization" required maxlength="120"></label>
          <label v-if="type==='teacher'">Subject or expertise<input v-model="form.subject" required maxlength="120"></label>
          <label>Country<input v-model="form.country" required maxlength="80"></label><label>Time zone<input v-model="form.timezone" required maxlength="80"></label>
          <button class="button primary" :disabled="busy">{{busy?'Creating…':'Create account'}}</button>
          <button v-if="type==='student'" class="button subtle" type="button" @click="google">G · Continue with Google</button>
        </form>
      </section>
    </div>
  </main>
</template>

<style scoped>
.application-shell{min-height:100vh;padding:30px 6vw;background:#f5effb;color:#443650}.application-shell header{display:flex;justify-content:space-between;align-items:center}.application-shell header strong{font-size:34px}.application-layout{display:grid;grid-template-columns:1fr 1fr;gap:7vw;max-width:1200px;margin:60px auto}.application-layout aside{padding-top:30px}.application-layout h1{font-size:54px;line-height:1.2;margin:24px 0}.application-layout em{font-style:normal;color:#9875b9}.application-art{font-size:70px;color:#a38ac0;padding:40px;text-align:center}.application-art span{font-size:120px;color:#b8cbbc}.application-form{padding:36px}.application-form h2{font-size:25px}.application-form label{display:grid;gap:8px;font-size:12px;margin:18px 0}.application-form input{padding:13px;border:1px solid #dfd1ec;border-radius:12px;background:#fffcff}.account-types{display:flex;gap:8px;margin:22px 0}.account-types button{flex:1;padding:12px;border:1px solid #d9c9e8;border-radius:12px}.account-types .active{background:#8d6bb1;color:white}.application-policy{background:#f2e9fa;padding:15px;border-radius:12px;line-height:1.7}.button{margin:6px 8px 6px 0}.error{color:#a3374e}@media(max-width:760px){.application-layout{grid-template-columns:1fr;margin:30px auto}.application-layout aside{display:none}.application-form{padding:25px}}
</style>
