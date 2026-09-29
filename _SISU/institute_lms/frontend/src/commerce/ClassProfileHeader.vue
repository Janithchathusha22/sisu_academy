<script setup>
import ClassTeacherIdentity from './ClassTeacherIdentity.vue'
defineProps({room:{type:Object,required:true},expanded:Boolean})
defineEmits(['open'])
</script>
<template><section class="class-profile-header" :class="{'is-expanded':expanded}">
  <div v-if="expanded" class="class-profile-banner"><img v-if="room.cover_image" :src="room.cover_image" alt="Classroom cover"></div>
  <div class="class-profile-content">
    <ClassTeacherIdentity :room="room"/>
    <div class="class-profile-titles">
      <div class="class-profile-teacher"><h2>{{room.teacher_profile?.display_name||room.teacher_name||'Your teacher'}}</h2><p v-if="room.teacher_profile?.qualifications" class="class-profile-qualifications">{{room.teacher_profile.qualifications}}</p></div>
      <div class="class-profile-subject"><h3 v-if="expanded" id="modal-title" :class="room.font">{{room.title}}</h3><button v-else type="button" :class="room.font" @click="$emit('open')">{{room.title}}</button><p v-if="room.grade&&!room.title?.includes(room.grade)">{{room.grade}}</p><p v-if="room.teaching_medium" class="class-profile-medium">{{room.teaching_medium}} medium</p></div>
    </div>
    <p v-if="room.description" class="class-profile-description" :class="{'clamp-2':!expanded}">{{room.description}}</p>
  </div>
</section></template>
<style scoped>
.class-profile-header{container-type:inline-size;color:var(--student-ink,#483953)}
.class-profile-titles{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:20px;align-items:start}
.class-profile-teacher h2{font-size:25px;font-weight:750;line-height:1.2;letter-spacing:-.6px;margin:0;overflow-wrap:anywhere}
.class-profile-qualifications{font-size:12px;line-height:1.6;margin:8px 0 0;font-weight:600}
.class-profile-subject{text-align:end}
.class-profile-subject h3,.class-profile-subject button{font-size:19px;line-height:1.35;font-weight:650;text-align:inherit;margin:0;padding:0;color:inherit;overflow-wrap:anywhere}
.class-profile-subject button:hover{color:var(--student-accent,#8968ab)}
.class-profile-subject p{font-size:12px;line-height:1.6;margin:5px 0 0}
.class-profile-medium{font-weight:600}
.class-profile-description{font-size:13px;line-height:1.8;margin:20px 0;color:var(--student-muted,#786888)}
.class-profile-banner{height:240px;background:linear-gradient(120deg,#d5c3e7,#e4dcf1);overflow:hidden}
.class-profile-banner img{width:100%;height:100%;object-fit:cover}
.is-expanded .class-profile-content{padding:0 32px 18px}
.is-expanded .class-profile-teacher h2{font-size:36px}
.is-expanded .class-profile-subject h3{font-size:25px}
.is-expanded :deep(.class-teacher-identity){margin-top:-76px;min-height:150px}
.is-expanded :deep(.class-teacher-photo){width:150px;height:150px;flex-basis:150px;border-width:6px}
.is-expanded :deep(.provider-social-links){padding-top:90px;max-width:300px}
@container(max-width:400px){.class-profile-titles{grid-template-columns:1fr;gap:14px}.class-profile-subject{text-align:start}.class-profile-teacher h2{font-size:24px}.class-profile-subject button{font-size:17px}}
@media(max-width:600px){.class-profile-banner{height:160px}.is-expanded .class-profile-content{padding:0 20px 12px}.is-expanded .class-profile-teacher h2{font-size:28px}.is-expanded .class-profile-subject h3{font-size:20px}.is-expanded :deep(.class-teacher-identity){margin-top:-48px;min-height:112px}.is-expanded :deep(.class-teacher-photo){width:106px;height:106px;flex-basis:106px;border-width:4px}.is-expanded :deep(.provider-social-links){padding-top:57px;max-width:180px}}
</style>
