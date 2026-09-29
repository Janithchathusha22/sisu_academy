// Retired browser-only mutations. Provider data is read through profiles APIs.
export const community=()=>({profiles:[],pending:[],links:[]})
const retired=()=>{throw Error('Use the authenticated profile service.')}
export const createProfile=retired,approveProfile=retired,relationship=retired,changeLink=retired,storeCommunity=retired
