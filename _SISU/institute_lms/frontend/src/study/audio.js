// Original, procedurally synthesized soundscapes. No streamed or downloaded tracks.
// Audio starts only inside a user's Play action; stop/dispose releases all nodes.
export function createStudyAudio(){
 let context,source,gain,request=0
 function stop(){request++;if(source){source.stop();source.disconnect();source=null}}
 async function play(kind,volume){
  stop();const id=request;context=context||new AudioContext();await context.resume();if(id!==request)return false
  if(!gain){gain=context.createGain();gain.connect(context.destination)}gain.gain.value=volume
  const seconds=kind==='rain'?8:32,rate=context.sampleRate,buffer=context.createBuffer(2,seconds*rate,rate)
  for(let channel=0;channel<2;channel++){
   const samples=buffer.getChannelData(channel);let brown=0,previous=0
   for(let i=0;i<samples.length;i++){
    const t=i/rate
    if(kind==='rain'){brown=(brown+(Math.random()*2-1)*.025)/1.025;const white=Math.random()*2-1;previous=.6*previous+.4*white;samples[i]=brown*.55+previous*.12}
    else{
     const notes=kind==='piano'?[261.63,329.63,392,493.88,440,392,329.63,293.66]:[130.81,164.81,196,220,196,164.81,146.83,164.81]
     const beat=Math.floor(t/4),local=t%4,f=notes[beat%notes.length],attack=Math.min(1,local/.045),decay=Math.exp(-local*(kind==='piano'?1.25:.7))
     const note=(Math.sin(2*Math.PI*f*t)+.28*Math.sin(2*Math.PI*f*2*t)+.08*Math.sin(2*Math.PI*f*3*t))*attack*decay
     const pad=(Math.sin(2*Math.PI*65.406*t)+Math.sin(2*Math.PI*98*t))*.07*Math.sin(Math.PI*t/seconds)**2
     const edge=Math.min(1,t/.03,(seconds-t)/.1)
     samples[i]=(note*.14+pad)*edge*(channel===0?1:.94)
    }
   }
  }
  source=context.createBufferSource();source.buffer=buffer;source.loop=true;source.connect(gain);source.start();return true
 }
 return {play,stop,volume(value){if(gain&&context)gain.gain.setTargetAtTime(value,context.currentTime,.08)},async dispose(){stop();gain?.disconnect();if(context)await context.close();context=null;gain=null}}
}
