import test from 'node:test'
import assert from 'node:assert/strict'
import {createTimer,startTimer,pauseTimer,displayedTime,elapsedTime,isFinished,formatTimer,restoreTimer,hasStudyPlus} from '../src/study/timer.js'
import {minorAmount,revenueQuote,schoolQuote,legacyQuote} from '../src/pricing.js'

test('focus time uses timestamps, survives suspension and pauses without drift',()=>{
 let timer=startTimer(createTimer('focus',25),1000)
 assert.equal(displayedTime(timer,61000),24*60000)
 timer=pauseTimer(timer,91000)
 assert.equal(displayedTime(timer,999000),23.5*60000)
 timer=startTimer(restoreTimer(timer),1000000)
 assert.equal(displayedTime(timer,1001000),1409000)
 assert(isFinished(timer,99999999))
 assert.equal(displayedTime(timer,99999999),0)
})
test('stopwatch grows, has a bounded session and malformed stored data resets',()=>{
 const timer=startTimer(createTimer('stopwatch'),1000)
 assert.equal(elapsedTime(timer,62000),61000)
 assert.equal(formatTimer(displayedTime(timer,62000)),'00:01:01')
 assert.equal(elapsedTime(timer,1),0)
 assert(isFinished(timer,90000000))
 assert.deepEqual(restoreTimer({mode:'focus',duration:Infinity}),createTimer())
 assert.throws(()=>createTimer('focus',181))
})
test('Study Plus expires exactly and account data cannot use a different product',()=>{
 const e={product:'study_plus',expiresAt:1000}
 assert(hasStudyPlus(e,999));assert(!hasStudyPlus(e,1000))
 assert(!hasStudyPlus({...e,product:'gpa'},999));assert(!hasStudyPlus(null))
})
test('source pricing examples use exact minor units and explicit fee reversal',()=>{
 const q=revenueQuote({gross:minorAmount('500000'),rateBps:250})
 assert.equal(q.platformFee,1250000);assert.equal(q.net,48750000)
 assert.equal(revenueQuote({gross:1000000,rateBps:700}).platformFee,70000)
 const r=revenueQuote({gross:100000,rateBps:250,refund:20000,gateway:3000,tax:1000})
 assert.equal(r.reversal,500);assert.equal(r.platformFee,2000);assert.equal(r.net,74000)
 assert.equal(revenueQuote({gross:100000,rateBps:250,refund:20000,reverseFee:false}).platformFee,2500)
 assert.equal(minorAmount('12.01'),1201)
 for(const value of ['1.001','NaN','-1','1e3'])assert.throws(()=>minorAmount(value))
 assert.throws(()=>revenueQuote({gross:100,rateBps:250,refund:101}))
})
test('institutional discounts are explicit and legacy pricing is never stacked',()=>{
 assert.equal(schoolQuote({activeStudents:500,unitMinor:10000}).total,5000000)
 assert.throws(()=>schoolQuote({activeStudents:500,unitMinor:10000,discountBps:1000}))
 assert.equal(schoolQuote({activeStudents:501,unitMinor:10000,discountBps:1000}).total,4509000)
 assert.throws(()=>schoolQuote({activeStudents:2000,unitMinor:10000,discountBps:2000}))
 assert.equal(schoolQuote({activeStudents:2001,unitMinor:10000,discountBps:2000}).total,16008000)
 assert(schoolQuote({activeStudents:10001,unitMinor:10000}).requiresQuote)
 assert.equal(legacyQuote(528,1500000).total,1640000)
 assert.throws(()=>schoolQuote({activeStudents:1.5,unitMinor:100}))
})
