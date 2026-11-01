"use strict";
(() => {
const canvas=document.getElementById("neural3d");
if(!canvas)return;
const fallback=document.getElementById("fallback3d");
const gl=canvas.getContext("webgl",{alpha:true,antialias:true});
if(!gl){canvas.hidden=true;if(fallback)fallback.hidden=false;return}
const VERTEX="attribute vec3 p; attribute float a; uniform mat4 projection; uniform mat4 model; uniform float pointSize; varying float alpha; void main(){vec4 pos=model*vec4(p,1.); gl_Position=projection*pos; gl_PointSize=max(1.,min(14.,pointSize*7./(-pos.z)));alpha=a;}";
const FRAGMENT="precision mediump float;uniform vec3 color;uniform float opacity;uniform float points; varying float alpha; void main(){float o=opacity*alpha; if(points>0.5){o*=smoothstep(.5,.05,length(gl_PointCoord-.5));}gl_FragColor=vec4(color,o);}";
function compile(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
let program;try{program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,VERTEX));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,FRAGMENT));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error("Link failed")}
catch(e){console.warn(e);canvas.hidden=true;if(fallback)fallback.hidden=false;return}
gl.useProgram(program);const p=gl.getAttribLocation(program,"p"),a=gl.getAttribLocation(program,"a"),projection=gl.getUniformLocation(program,"projection"),model=gl.getUniformLocation(program,"model"),pointSize=gl.getUniformLocation(program,"pointSize"),color=gl.getUniformLocation(program,"color"),opacity=gl.getUniformLocation(program,"opacity"),points=gl.getUniformLocation(program,"points");
const PI=Math.PI;
function object(data,mode,rgb,alpha){const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);return {buf,mode,rgb,alpha,count:data.length/4}}
function sphere(){const v=[];for(let j=1;j<25;j++){const lat=j*PI/25;for(let i=0;i<80;i++){const lon=i*PI/40;v.push(.9*Math.sin(lat)*Math.cos(lon),.9*Math.cos(lat),.9*Math.sin(lat)*Math.sin(lon),.4+.6*Math.sin(lat))}}return object(v,gl.POINTS,[.23,.9,1],.78)}
function torus(radius){const v=[];for(let i=0;i<260;i++){const t=2*PI*i/260,u=2*PI*(i+1)/260;v.push(radius*Math.cos(t),0,radius*Math.sin(t),.3+.7*(.5+.5*Math.cos(t*8)),radius*Math.cos(u),0,radius*Math.sin(u),.3+.7*(.5+.5*Math.cos(t*8)))}return object(v,gl.LINES,[.23,.91,1],.72)}
let seed=37;function rand(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296}const particles=[];for(let i=0;i<520;i++){const z=rand()*2-1,phi=rand()*2*PI,rad=1.5+rand()*1.5;particles.push(rad*Math.sqrt(1-z*z)*Math.cos(phi),rad*z,rad*Math.sqrt(1-z*z)*Math.sin(phi),.3+rand()*.7)}
const core=sphere(),rings=[torus(1.2),torus(1.49),torus(1.8)],dust=object(particles,gl.POINTS,[.25,.7,1],.55);
// Only public, observed tool lifecycle can create graph nodes.
const toolNodes=new Map();
function fibonacci(i,count){const y=1-(i+.5)*2/Math.max(1,count),theta=i*2.399963229728653;const k=Math.sqrt(Math.max(0,1-y*y));return [Math.cos(theta)*k*2.37,y*2.37,Math.sin(theta)*k*2.37]}
function graphMesh(){const wires=[],active=[],complete=[],errors=[];const nodes=Array.from(toolNodes.values());for(let i=0;i<nodes.length;i++){const pos=fibonacci(i,Math.max(nodes.length,6));wires.push(0,0,0,.24,...pos,.55);const dest=nodes[i].state==="running"?active:nodes[i].state==="error"?errors:complete;for(let j=0;j<9;j++){const angle=j*2*PI/9;dest.push(pos[0]+Math.cos(angle)*.075,pos[1]+Math.sin(angle)*.075,pos[2],.9)}}return {wires:object(wires,gl.LINES,[.3,.75,.94],.6),active:object(active,gl.POINTS,[.38,1,.93],1),complete:object(complete,gl.POINTS,[.25,.6,.95],.77),errors:object(errors,gl.POINTS,[1,.35,.37],1)}}
let graph=null;
function updateNetwork(item){if(!item||typeof item.tool_id!=="number"||item.tool_id<1||item.tool_id>18)return;const state=["running","completed","error","unknown"].includes(item.tool_state)?item.tool_state:"unknown";toolNodes.set(item.tool_id,{state});if(toolNodes.size>18){const first=toolNodes.keys().next().value;toolNodes.delete(first)}graph=graphMesh()}
function resetNetwork(){toolNodes.clear();graph=null}
const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
let state="idle",target=0,level=0,phase=0,last=performance.now();
function rotate(rx,ry,rz,scale){const cx=Math.cos(rx),sx=Math.sin(rx),cy=Math.cos(ry),sy=Math.sin(ry),cz=Math.cos(rz),sz=Math.sin(rz);return new Float32Array([cy*cz*scale,cy*sz*scale,-sy*scale,0,(sx*sy*cz-cx*sz)*scale,(sx*sy*sz+cx*cz)*scale,sx*cy*scale,0,(cx*sy*cz+sx*sz)*scale,(cx*sy*sz-sx*cz)*scale,cx*cy*scale,0,0,0,-7.1,1])}
function draw(o,m,alpha,size){gl.bindBuffer(gl.ARRAY_BUFFER,o.buf);gl.enableVertexAttribArray(p);gl.enableVertexAttribArray(a);gl.vertexAttribPointer(p,3,gl.FLOAT,false,16,0);gl.vertexAttribPointer(a,1,gl.FLOAT,false,16,12);gl.uniformMatrix4fv(model,false,m);gl.uniform3fv(color,o.rgb);gl.uniform1f(opacity,Math.min(1,o.alpha*alpha));gl.uniform1f(points,o.mode===gl.POINTS?1:0);gl.uniform1f(pointSize,size);gl.drawArrays(o.mode,0,o.count)}
function size(){const ratio=Math.min(2,devicePixelRatio||1),w=Math.max(1,Math.round(canvas.clientWidth*ratio)),h=Math.max(1,Math.round(canvas.clientHeight*ratio));if(w===canvas.width&&h===canvas.height)return;canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);const n=.1,f=50,k=1/Math.tan(40*PI/360);gl.uniformMatrix4fv(projection,false,new Float32Array([k*h/w,0,0,0,0,k,0,0,0,0,(f+n)/(n-f),-1,0,0,2*f*n/(n-f),0]))}
gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.disable(gl.DEPTH_TEST);
window.UltronNeural={setState:s=>{if(s!=="audio_level")state=s},setLevel:n=>{target=Math.min(1,Math.max(0,Number(n)||0))},updateNetwork,resetNetwork};
function frame(now){const dt=Math.min(.07,(now-last)/1000);last=now;phase+=reduced?0:dt;level+=(target-level)*Math.min(1,dt*15);target*=Math.exp(-dt*4);const speak=state==="speaking",think=state==="thinking",energy=speak?level:think?.33:state==="listening"?.15:.08;size();gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);const spin=phase*(think?.8:speak?.4:.18),grow=1+energy*.14;
draw(dust,rotate(spin*.1,spin*.14,0,1),.32+energy*.5,10);draw(core,rotate(.35+spin*.12,spin*.61,spin*.09,grow),.65+energy*.36,13);
for(let i=0;i<3;i++){const x=(i%2?-1:1)*spin*(i*.3+1),m=rotate(.4+i*.66+x*.25,i*1.3+x,.3+i*.55,1+energy*.075);draw(rings[i],m,.6+energy*.67,4)}
if(graph){const orientation=rotate(.1+spin*.12,spin*.17,0,1);draw(graph.wires,orientation,.43+energy*.4,4);draw(graph.active,orientation,.7+(.3*Math.sin(phase*4)**2),15);draw(graph.complete,orientation,.6,13);draw(graph.errors,orientation,.95,16)}
const halo=document.getElementById("coreHalo");if(halo){halo.style.transform="translate(-50%,-50%) scale("+(1+energy*.23)+")";halo.style.opacity=String(Math.min(1,.35+energy*.75))}
requestAnimationFrame(frame)}
requestAnimationFrame(frame);
})();