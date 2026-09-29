<script setup>defineProps({network:String})</script>
<template><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
<path v-if="network==='facebook'" d="M14 22v-9h3l.5-4H14V7c0-1.2.4-2 2-2h2V1.4C17.2 1.2 16.1 1 15 1c-3 0-5 1.8-5 5v3H7v4h3v9z"/>
<g v-else-if="network==='instagram'" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></g>
<path v-else-if="network==='youtube'" fill-rule="evenodd" d="M22 7s-.2-2-2-2.5C18.3 4 12 4 12 4s-6.3 0-8 .5C2.2 5 2 7 2 7s-.5 2-.5 5 .5 5 .5 5 .2 2 2 2.5c1.7.5 8 .5 8 .5s6.3 0 8-.5c1.8-.5 2-2.5 2-2.5s.5-2 .5-5S22 7 22 7ZM10 8v8l6-4z"/>
<g v-else-if="network==='linkedin'"><rect x="3" y="9" width="4" height="12"/><circle cx="5" cy="4.8" r="2.3"/><path d="M10 9h4v1.6c1-1.4 2.2-2 3.7-2 3.2 0 4.3 2.1 4.3 5.4v7h-4v-6.5c0-1.7-.3-2.8-1.9-2.8-1.5 0-2.1 1.1-2.1 2.8V21h-4z"/></g>
<path v-else-if="network==='twitter'" d="M18.9 2H22l-6.8 7.8L23 22h-6.2L12 14.5 5.5 22H2.3l8.2-9.5L1 2h6.4l5.8 7.4L18.9 2ZM6 4H4.8l13.1 16h1.3L6 4Z"/>
<path v-else-if="network==='tiktok'" d="M14 2h4c.3 2.6 1.9 4.3 4 4.7v4a11 11 0 0 1-4-1.5v7A6.5 6.5 0 1 1 10 10v4a2.6 2.6 0 1 0 4 2.2V2Z"/>
</svg></template>
