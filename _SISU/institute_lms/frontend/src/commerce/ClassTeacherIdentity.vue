<script setup>
import {computed} from 'vue'
import SocialLinks from './SocialLinks.vue'
const props=defineProps({room:{type:Object,required:true}})
const profile=computed(()=>props.room.teacher_profile||{kind:'Teacher',display_name:props.room.teacher_name,profile_image:props.room.profile_image,socials:{}})
</script>
<template><div class="class-teacher-identity"><div class="class-teacher-photo"><img v-if="profile.profile_image||room.profile_image" :src="profile.profile_image||room.profile_image" :alt="profile.display_name||room.teacher_name||'Teacher'" loading="lazy"><span v-else>{{(room.teacher_name||'Teacher').slice(0,1)}}</span></div><SocialLinks :profile="profile"/></div></template>
<style scoped>
.class-teacher-identity{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;position:relative;margin:-52px 0 18px;min-height:110px}
.class-teacher-photo{width:110px;height:110px;flex:0 0 110px;border:5px solid var(--student-card,#fff);border-radius:50%;overflow:hidden;background:var(--student-soft,#eee4f6);box-shadow:0 7px 20px #5c3b7120;display:grid;place-items:center;font-size:36px;color:var(--student-ink,#514064)}
.class-teacher-photo img{width:100%;height:100%;object-fit:cover}
.class-teacher-identity :deep(.provider-social-links){justify-content:flex-end;padding-top:44px;gap:5px;max-width:288px}
.class-teacher-identity :deep(.provider-social-links a),.class-teacher-identity :deep(.provider-social-links button){width:36px;min-height:44px;border-radius:12px;box-shadow:none}
.class-teacher-identity :deep(.provider-social-links svg){width:20px;height:20px}
@media(max-width:600px){.class-teacher-identity{gap:12px;margin-top:-45px;min-height:92px}.class-teacher-photo{width:92px;height:92px;flex-basis:92px;border-width:4px}.class-teacher-identity :deep(.provider-social-links){padding-top:37px;max-width:180px}}
</style>
