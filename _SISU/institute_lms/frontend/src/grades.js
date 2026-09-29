export const demoScale={'A':4,'A-':3.7,'B+':3.3,'B':3,'B-':2.7,'C+':2.3,'C':2,'C-':1.7,'D':1,'F':0}
export function calculateGpa(rows){
 const included=rows.filter(r=>!r.excluded)
 if(included.some(r=>!Number.isFinite(Number(r.credits))||Number(r.credits)<=0||Number(r.credits)>60||r.points===''||!Number.isFinite(Number(r.points))||Number(r.points)<0||Number(r.points)>4))throw Error('Use positive credits up to 60 and grade points from 0 to 4 for this scale')
 const credits=included.reduce((s,r)=>s+Number(r.credits),0),points=included.reduce((s,r)=>s+Number(r.credits)*Number(r.points),0)
 return {credits,weightedPoints:points,gpa:credits?points/credits:null}
}
