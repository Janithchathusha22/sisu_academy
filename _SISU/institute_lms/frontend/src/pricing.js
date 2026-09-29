// Draft commercial catalog reconciled from the two supplied pricing documents.
// These quotes never settle invoices, authorize a payout, or grant paid entitlements.
export const marketTiers=[
 {id:'A',title:'Value',bps:250},{id:'B',title:'Emerging',bps:300},{id:'C',title:'Growth',bps:400},{id:'D',title:'High-value',bps:500},{id:'E',title:'Premium contract',bps:700}
]
export const institutionalRates=[{id:'lk',title:'Sri Lanka launch',currency:'LKR',minor:10000},{id:'emerging',title:'Emerging reference',currency:'USD',minor:100},{id:'growth',title:'Growth reference',currency:'USD',minor:250},{id:'developed5',title:'Developed reference · lower',currency:'USD',minor:500},{id:'developed8',title:'Developed reference · upper',currency:'USD',minor:800},{id:'gulf',title:'Premium Gulf ceiling',currency:'USD',minor:1000}]
export function minorAmount(value){const s=String(value).trim();if(!/^\d{1,9}(\.\d{1,2})?$/.test(s))throw Error('Enter a non-negative amount with at most two decimal places');const [whole,decimals='']=s.split('.');return Number(whole)*100+Number(decimals.padEnd(2,'0'))}
function integer(value,min,max,label){if(!Number.isSafeInteger(value)||value<min||value>max)throw Error(label);return value}
export function revenueQuote({gross,rateBps,gateway=0,tax=0,refund=0,reverseFee=true}){
 integer(gross,0,99999999999,'Invalid gross amount');integer(rateBps,0,10000,'Invalid platform rate');integer(gateway,0,gross,'Invalid gateway fee');integer(tax,0,gross,'Invalid tax');integer(refund,0,gross,'Refund cannot exceed collected amount')
 const originalFee=Math.round(gross*rateBps/10000),reversal=reverseFee?Math.round(refund*rateBps/10000):0,platformFee=originalFee-reversal,net=gross-refund-platformFee-gateway-tax
 return {gross,refund,originalFee,reversal,platformFee,gateway,tax,net}
}
export function schoolQuote({activeStudents,unitMinor,discountBps=0}){
 integer(activeStudents,0,1000000,'Invalid active student count');integer(unitMinor,0,10000000,'Invalid student rate');integer(discountBps,0,2000,'Invalid discount')
 const ceiling=activeStudents<=500?0:activeStudents<=2000?1000:2000
 if(discountBps>ceiling)throw Error('The chosen discount exceeds the document’s volume guidance')
 const subtotal=activeStudents*unitMinor,discount=Math.round(subtotal*discountBps/10000)
 return {subtotal,discount,total:subtotal-discount,requiresQuote:activeStudents>10000}
}
export function legacyQuote(activeStudents,baseMinor){integer(activeStudents,0,1000000,'Invalid student count');integer(baseMinor,0,99999999999,'Invalid base fee');const extra=Math.max(0,activeStudents-500);return {extra,total:baseMinor+extra*5000}}
export const formatMoney=(minor,currency='LKR')=>new Intl.NumberFormat('en',{style:'currency',currency,maximumFractionDigits:2}).format(minor/100)
