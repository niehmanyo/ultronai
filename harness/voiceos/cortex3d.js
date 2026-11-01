"use strict";
(() => {
const canvas=document.getElementById("neural3d");
if(!canvas)return;
const fallback=document.getElementById("fallback3d");
const gl=canvas.getContext("webgl",{alpha:true,antialias:true});
if(!gl){canvas.hidden=true;if(fallback)fallback.hidden=false;return}
const VERTEX="attribute vec3 p; attribute float a; uniform mat4 projection; uniform mat4 model; uniform float pointSize; uniform float time; uniform float activity; uniform float shell; varying float alpha; varying float depthCue; void main(){vec3 q=p; if(shell>0.5){float wave=sin(p.x*9.+time*1.5)+sin(p.y*11.-time*1.1)+cos(p.z*8.+time*.65);q*=1.+activity*.075+wave*(.012+.013*activity);} vec4 pos=model*vec4(q,1.); gl_Position=projection*pos; gl_PointSize=max(1.,min(16.,pointSize*7./(-pos.z)));alpha=a;depthCue=clamp((pos.z+10.)/6.,.18,1.);}";
const FRAGMENT="precision mediump float;uniform vec3 color;uniform float opacity;uniform float points; varying float alpha;varying float depthCue; void main(){float o=opacity*alpha*depthCue; if(points>0.5){o*=smoothstep(.5,.05,length(gl_PointCoord-.5));}gl_FragColor=vec4(color,o);}";
function compile(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
let program;try{program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,VERTEX));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,FRAGMENT));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error("Link failed")}
catch(e){console.warn(e);canvas.hidden=true;if(fallback)fallback.hidden=false;return}
gl.useProgram(program);const p=gl.getAttribLocation(program,"p"),a=gl.getAttribLocation(program,"a"),projection=gl.getUniformLocation(program,"projection"),model=gl.getUniformLocation(program,"model"),pointSize=gl.getUniformLocation(program,"pointSize"),color=gl.getUniformLocation(program,"color"),opacity=gl.getUniformLocation(program,"opacity"),points=gl.getUniformLocation(program,"points");
const timeUniform=gl.getUniformLocation(program,"time"),activityUniform=gl.getUniformLocation(program,"activity"),shellUniform=gl.getUniformLocation(program,"shell");
const PI=Math.PI;
function object(data,mode,rgb,alpha){const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);return {buf,mode,rgb,alpha,count:data.length/4}}
function denseSphere(count,radius,rgb,alpha,inside=false){const v=[];const golden=PI*(3-Math.sqrt(5));for(let i=0;i<count;i++){const y=1-2*(i+.5)/count,spread=Math.sqrt(1-y*y),theta=i*golden,dist=radius*(inside?Math.cbrt(.05+.95*((i*229+71)%count)/count):1+Math.sin(i*4.7)*.012);v.push(dist*spread*Math.cos(theta),dist*y,dist*spread*Math.sin(theta),.36+.64*(.5+.5*Math.sin(i*17.17))) }return object(v,gl.POINTS,rgb,alpha)}
function torus(radius){const v=[];for(let i=0;i<260;i++){const t=2*PI*i/260,u=2*PI*(i+1)/260;v.push(radius*Math.cos(t),0,radius*Math.sin(t),.3+.7*(.5+.5*Math.cos(t*8)),radius*Math.cos(u),0,radius*Math.sin(u),.3+.7*(.5+.5*Math.cos(t*8)))}return object(v,gl.LINES,[.23,.91,1],.72)}
let seed=37;function rand(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296}const particles=[];for(let i=0;i<1150;i++){const z=rand()*2-1,phi=rand()*2*PI,rad=1.3+rand()*2.0;particles.push(rad*Math.sqrt(1-z*z)*Math.cos(phi),rad*z,rad*Math.sqrt(1-z*z)*Math.sin(phi),.15+rand()*.76)}
const core=denseSphere(2400,.91,[.31,.98,1],.88),inner=denseSphere(1150,.91,[.14,.56,.86],.54,true),outer=denseSphere(1050,1.22,[.23,.66,1],.42),rings=[torus(1.38),torus(1.72),torus(2.08)],dust=object(particles,gl.POINTS,[.25,.7,1],.55);
// Fixed constellation arcs: geometric neural patterns, not claims of actual reasoning.
const connections=[];for(let i=0;i<180;i++){const a=i*2.399963229728653,b=(i+13)*2.399963229728653;const y=1-2*(i+.5)/180,yy=1-2*((i+13)%180+.5)/180;const k=Math.sqrt(1-y*y),kk=Math.sqrt(1-yy*yy);if(Math.abs(i-(i+13)%180)<1)continue;connections.push(.96*k*Math.cos(a),.96*y,.96*k*Math.sin(a),.1,.96*kk*Math.cos(b),.96*yy,.96*kk*Math.sin(b),.1)}const netLines=object(connections,gl.LINES,[.19,.74,.86],.28);
// Only public, observed tool lifecycle can create graph nodes.
const toolNodes=new Map();
function fibonacci(i,count){const y=1-(i+.5)*2/Math.max(1,count),theta=i*2.399963229728653;const k=Math.sqrt(Math.max(0,1-y*y));return [Math.cos(theta)*k*2.37,y*2.37,Math.sin(theta)*k*2.37]}
function disposeGraph(){if(!graph)return;for(const item of Object.values(graph)){gl.deleteBuffer(item.buf)}}
function graphMesh(){const wires=[],active=[],complete=[],errors=[];const nodes=Array.from(toolNodes.values());for(let i=0;i<nodes.length;i++){const pos=fibonacci(i,Math.max(nodes.length,6));wires.push(0,0,0,.24,...pos,.55);const dest=nodes[i].state==="running"?active:nodes[i].state==="error"?errors:complete;for(let j=0;j<9;j++){const angle=j*2*PI/9;dest.push(pos[0]+Math.cos(angle)*.075,pos[1]+Math.sin(angle)*.075,pos[2],.9)}}return {wires:object(wires,gl.LINES,[.3,.75,.94],.6),active:object(active,gl.POINTS,[.38,1,.93],1),complete:object(complete,gl.POINTS,[.25,.6,.95],.77),errors:object(errors,gl.POINTS,[1,.35,.37],1)}}
let graph=null;
function updateNetwork(item){if(!item||typeof item.tool_id!=="number"||item.tool_id<1||item.tool_id>18)return;const state=["running","completed","error","unknown"].includes(item.tool_state)?item.tool_state:"unknown";toolNodes.set(item.tool_id,{state});if(toolNodes.size>18){const first=toolNodes.keys().next().value;toolNodes.delete(first)}disposeGraph();graph=graphMesh()}
function resetNetwork(){toolNodes.clear();disposeGraph();graph=null}
const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
let state="idle",target=0,level=0,phase=0,last=performance.now();
function rotate(rx,ry,rz,scale){const cx=Math.cos(rx),sx=Math.sin(rx),cy=Math.cos(ry),sy=Math.sin(ry),cz=Math.cos(rz),sz=Math.sin(rz);return new Float32Array([cy*cz*scale,cy*sz*scale,-sy*scale,0,(sx*sy*cz-cx*sz)*scale,(sx*sy*sz+cx*cz)*scale,sx*cy*scale,0,(cx*sy*cz+sx*sz)*scale,(cx*sy*sz-sx*cz)*scale,cx*cy*scale,0,0,0,-6.05,1])}
function draw(o,m,alpha,size,shell=0){gl.bindBuffer(gl.ARRAY_BUFFER,o.buf);gl.enableVertexAttribArray(p);gl.enableVertexAttribArray(a);gl.vertexAttribPointer(p,3,gl.FLOAT,false,16,0);gl.vertexAttribPointer(a,1,gl.FLOAT,false,16,12);gl.uniformMatrix4fv(model,false,m);gl.uniform3fv(color,o.rgb);gl.uniform1f(opacity,Math.min(1,o.alpha*alpha));gl.uniform1f(points,o.mode===gl.POINTS?1:0);gl.uniform1f(pointSize,size);gl.uniform1f(shellUniform,shell);gl.drawArrays(o.mode,0,o.count)}
function size(){const ratio=Math.min(2,devicePixelRatio||1),w=Math.max(1,Math.round(canvas.clientWidth*ratio)),h=Math.max(1,Math.round(canvas.clientHeight*ratio));if(w===canvas.width&&h===canvas.height)return;canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);const n=.1,f=50,k=1/Math.tan(40*PI/360);gl.uniformMatrix4fv(projection,false,new Float32Array([k*h/w,0,0,0,0,k,0,0,0,0,(f+n)/(n-f),-1,0,0,2*f*n/(n-f),0]))}
gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.enable(gl.DEPTH_TEST);gl.depthMask(false);
window.UltronNeural={setState:s=>{if(s!=="audio_level")state=s},setLevel:n=>{target=Math.min(1,Math.max(0,Number(n)||0))},updateNetwork,resetNetwork};
function frame(now){
const dt=Math.min(.07,Math.max(0,(now-last)/1000));last=now;if(!document.hidden)phase+=reduced?0:dt;
level+=(target-level)*Math.min(1,dt*14);target*=Math.exp(-dt*3.6);
const speak=state==="speaking",think=state==="thinking";
const energy=speak?level:think?.42:state==="listening"?.14:.065;
size();gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
gl.uniform1f(timeUniform,phase);gl.uniform1f(activityUniform,energy);
const spin=phase*(think?.65:speak?.38:.12),grow=1+energy*.10;
const rotationCore=rotate(.34+spin*.08,spin*.56,.2+spin*.12,grow);
draw(dust,rotate(spin*.06,spin*.10,0,1),.23+energy*.38,7);
draw(outer,rotate(.13-spin*.13,-spin*.4,.28,1+energy*.085),.33+energy*.25,10,1);
draw(inner,rotate(-.22+spin*.18,-spin*.31,0,1+energy*.13),.38+energy*.27,8,1);
draw(netLines,rotationCore,think?.8:.24,2);
draw(core,rotationCore,.75+energy*.36,13,1);
for(let i=0;i<3;i++){
 const sign=i%2?-1:1,theta=spin*sign*(1+i*.15);
 draw(rings[i],rotate(.38+i*.68+theta*.12,i*1.26+theta,.22+i*.53,1+energy*.062),.34+energy*.57,3);
}
if(graph){
const t=rotate(.1+spin*.12,spin*.17,0,1);
draw(graph.wires,t,.43+energy*.4,3);
draw(graph.active,t,.72+.24*Math.sin(phase*4)**2,16);
draw(graph.complete,t,.66,14);
draw(graph.errors,t,.94,16);
}
const halo=document.getElementById("coreHalo");
if(halo){halo.style.transform="translate(-50%,-50%) scale("+(1+energy*.3)+")";halo.style.opacity=String(Math.min(1,.33+energy*.7))}
requestAnimationFrame(frame)
}
requestAnimationFrame(frame);
})();