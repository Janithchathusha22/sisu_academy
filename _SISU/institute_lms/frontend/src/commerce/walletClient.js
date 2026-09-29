import {call} from '../service'
export const walletCall=(method,args)=>call(method,args,'wallet')
export function localExport(rows){return '\ufeffPayout reference,Wallet,Amount,Currency,Status\r\n'+rows.map(r=>[r.name,r.wallet,(r.amount_minor/100).toFixed(2),r.currency,r.status].map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n')}
