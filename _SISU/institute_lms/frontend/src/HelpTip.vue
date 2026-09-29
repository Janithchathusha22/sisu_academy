<script setup>
import {ref,useId} from 'vue'
defineProps({text:String,label:{type:String,default:'More information'}})
const open=ref(false),id=useId()
</script>
<template><span class="help-tip" @mouseenter="open=true" @mouseleave="open=false"><button type="button" :aria-label="label" :aria-describedby="open?id:undefined" :aria-expanded="open" @focus="open=true" @blur="open=false" @click.stop="open=!open" @keydown.esc.stop="open=false">?</button><span v-if="open" :id="id" role="tooltip">{{text}}</span></span></template>
