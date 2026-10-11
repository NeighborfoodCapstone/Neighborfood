import { useEffect, useRef } from "react";
import "./trust-temperature.css";
export function TrustTemperature({ value }: { value: unknown }) {
  const host=useRef<HTMLElement>(null);
  const parsed=value == null || value === "" ? NaN : Number(value);
  const available=Number.isFinite(parsed);
  const temperature=available ? Math.min(40,Math.max(0,parsed)) : 0;
  useEffect(()=>{
    if (!available) return;

const root=host.current; if (!root) return;
const canvas=root.querySelector<HTMLCanvasElement>('canvas')!;
const context=canvas.getContext('2d'); if (!context) return; const ctx: CanvasRenderingContext2D=context;
const meter=root,value=root.querySelector<HTMLOutputElement>('output')!;
const reduce=matchMedia('(prefers-reduced-motion: reduce)');let temp=temperature,hover=false,pointerX=250,phase=0,w=500,frame=0; let release: ReturnType<typeof setTimeout> | undefined; let disposed=false;
const events=new AbortController(); const options={signal:events.signal};
function mix(a:number[],b:number[],t:number){return a.map((v,i)=>Math.round(v+(b[i]-v)*t));}
function color(){const blue=[49,150,230],orange=[235,151,52],red=[224,64,47];let c=temp<28?blue:temp<=36?mix(blue,orange,(temp-28)/8):mix(orange,red,(temp-36)/4);return 'rgb('+c.join(',')+')';}
function flame(x:number,y:number,size:number,offset:number){const sway=reduce.matches?0:Math.sin(phase*1.7+offset)*size*.15;const stretch=reduce.matches?1:1+Math.sin(phase*2.1+offset)*.15;
ctx.save();ctx.translate(x,y);ctx.beginPath();ctx.moveTo(-size*.42,0);ctx.bezierCurveTo(-size*.65,-size*.5,-size*.04+sway,-size*.55,size*.03+sway,-size*stretch);ctx.bezierCurveTo(size*.58,-size*.53,size*.6,-size*.32,size*.4,0);ctx.closePath();const g=ctx.createLinearGradient(0,0,0,-size);g.addColorStop(0,'#f28b35');g.addColorStop(.55,'#e84632');g.addColorStop(1,'#e8463200');ctx.fillStyle=g;ctx.fill();ctx.beginPath();ctx.moveTo(-size*.17,0);ctx.quadraticCurveTo(-size*.25,-size*.22,size*.02,-size*.48);ctx.quadraticCurveTo(size*.28,-size*.15,size*.18,0);ctx.fillStyle='#ffd180';ctx.fill();ctx.restore();}
function draw(){ctx.clearRect(0,0,w,140);const x=50,y=76,h=28,end=w-16,length=Math.max(1,end-x),fill=length*temp/40,c=color(),moving=hover&&!reduce.matches;const amplitude=1.5;
function localRipple(px:number){const distance=(px-pointerX)/42;return moving?Math.exp(-distance*distance/2)*3*Math.sin(px*.11-phase*3):0;}
// The reservoir and tube share a single liquid surface.
ctx.save();ctx.beginPath();ctx.roundRect(x-16,y,length+16,h,14);ctx.arc(30,y+h/2,22,0,Math.PI*2);ctx.fillStyle='#eceff1';ctx.fill();ctx.clip();
ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(0,y+7);
for(let px=0;px<=x+fill;px+=2){const wave=Math.sin(px*.055+phase*.65)*amplitude+localRipple(px);ctx.lineTo(px,y+6+wave);}
for(let py=y+6;py<=y+h+16;py+=2){const ripple=Math.sin(py*.2+phase*.65)*.7+(moving?Math.exp(-Math.pow((x+fill-pointerX)/42,2)/2)*Math.sin(py*.24+phase*3)*1.8:0);ctx.lineTo(Math.max(0,x+fill+ripple),py);}
ctx.lineTo(0,y+h+16);ctx.closePath();if(temp>0)ctx.fill();
const sheen=ctx.createLinearGradient(0,y,0,y+h);sheen.addColorStop(0,'#ffffff42');sheen.addColorStop(1,'#ffffff00');ctx.fillStyle=sheen;ctx.fill();
if(temp>0){ctx.fillStyle='#ffffff60';for(let i=0;i<3;i++){const bx=18+((phase*10+i*71)%Math.max(20,fill));const by=y+17+Math.sin(phase+i)*3;ctx.beginPath();ctx.arc(bx,by,1.3,0,Math.PI*2);ctx.fill();}}ctx.restore();
if(temp>36){const strength=(temp-36)/4,tip=x+fill;const count=3+Math.floor(strength*3);for(let i=0;i<count;i++){const fx=Math.max(x,tip-12-i*(8+strength*5));flame(fx,y+5,17+strength*23+(i%2)*7,i*1.7);}}
ctx.fillStyle='#a6adb3';ctx.fillRect(x+length*.9,y+h+7,1,5);
}
function animate(){frame=0;if(disposed || document.hidden)return;phase+=.045;draw();if(!reduce.matches){frame=requestAnimationFrame(animate);}}
function refresh(){if(!frame)animate();}
function update(n:number){temp=Math.min(40,Math.max(0,Number.isFinite(n)?n:0));value.textContent=temp.toFixed(1)+'°';canvas.setAttribute('aria-label','신뢰 온도 '+temp.toFixed(1)+'도, 최대 40도');refresh();}
function locate(e:PointerEvent){pointerX=e.clientX-canvas.getBoundingClientRect().left;}
meter.addEventListener('pointerenter',e=>{locate(e);hover=true;update(temp);},options);
meter.addEventListener('pointermove',e=>{locate(e);},options);meter.addEventListener('pointerleave',()=>{hover=false;update(temp);},options);meter.addEventListener('pointerdown',e=>{locate(e);clearTimeout(release);hover=true;update(temp);},options);meter.addEventListener('pointerup',()=>{release=setTimeout(()=>{hover=false;update(temp);},1000);},options);
reduce.addEventListener('change',()=>{if(frame){cancelAnimationFrame(frame);frame=0;}refresh();},options);
document.addEventListener('visibilitychange',()=>{if(frame){cancelAnimationFrame(frame);frame=0;}if(!document.hidden)refresh();},options);
const observer=new ResizeObserver(()=>{w=canvas.getBoundingClientRect().width||500;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(w*dpr);canvas.height=140*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);draw();});observer.observe(canvas);
update(temp);

return ()=>{disposed=true;events.abort();observer.disconnect();if(frame)cancelAnimationFrame(frame);clearTimeout(release);};
  },[temperature,available]);
  return <section ref={host} className="rx-trust-temperature" aria-label="신뢰 온도">
    <div className="rx-trust-value-row"><span>신뢰 온도</span><output aria-live="polite">{available ? temperature.toFixed(1)+"°" : "—"}</output></div>
    <canvas role="img" aria-label={available ? `신뢰 온도 ${temperature.toFixed(1)}도, 최대 40도` : "신뢰 온도를 확인할 수 없습니다"}/>
    <div className="rx-trust-ticks" aria-hidden="true"><span>0°</span><span style={{left:"50%"}}>20°</span><span style={{left:"90%"}}>36°</span><span>40°</span></div>
  </section>;
}
