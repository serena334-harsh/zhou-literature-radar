import {seed,mergePapers,type RadarData,type Paper,type Topic,type Action} from './data.ts';
export const LOCAL_KEY='zhou-literature-radar.local.v1';
export type LocalState={revision:number;papers:Paper[];topics:Topic[];actions:Action[];reviews:RadarData['reviews']};
export function compose(publicData:RadarData,local:LocalState|null):RadarData {
  if(!local)return structuredClone(publicData);
  const merge=<T extends {id:string}>(base:T[],updates:T[])=>[...new Map([...base,...updates].map(x=>[x.id,x])).values()];
  return {...publicData,papers:mergePapers(publicData.papers,local.papers).papers,topics:merge(publicData.topics,local.topics),actions:merge(publicData.actions,local.actions),reviews:local.reviews};
}
export function localChanges(publicData:RadarData,next:RadarData,revision:number):LocalState {
  const changed=<T extends {id:string}>(base:T[],items:T[])=>items.filter(x=>JSON.stringify(base.find(b=>b.id===x.id))!==JSON.stringify(x));
  return {revision,papers:changed(publicData.papers,next.papers),topics:changed(publicData.topics,next.topics),actions:changed(publicData.actions,next.actions),reviews:next.reviews};
}
let publicData:RadarData=structuredClone(seed);
function stored():LocalState|null {const raw=localStorage.getItem(LOCAL_KEY);if(!raw)return null;try{return JSON.parse(raw)}catch{throw new Error('本机备份数据无法读取，请先导出或检查浏览器存储')}}
function validate(data:any){if(data?.schemaVersion!==1||!['papers','topics','actions','reviews','reports'].every(k=>Array.isArray(data[k])))throw new Error('数据格式不匹配');for(const p of data.papers){if(typeof p.id!=='string'||typeof p.title!=='string'||!p.dimensions||!['target','resource','dofs','mechanism','topology'].every(k=>Array.isArray(p.dimensions[k]))||!/^https:\/\//.test(p.url))throw new Error('文献字段或来源链接不完整')}for(const k of ['papers','topics','actions'])if(new Set(data[k].map((x:any)=>x.id)).size!==data[k].length)throw new Error('数据包含重复标识')}
export async function radarFetch(_url:string,options?:RequestInit):Promise<Response>{
  try{if(options?.method==='POST'){const b=JSON.parse(options.body as string);if(b.action!=='save')throw new Error('公开页面只保存本机阅读与比较数据');validate(b.data);const current=stored();if((current?.revision||0)!==b.revision)throw new Error('另一窗口已更新本机数据，请重新读取后保存');const revision=b.revision+1;localStorage.setItem(LOCAL_KEY,JSON.stringify(localChanges(publicData,b.data,revision)));return Response.json({revision})}
    const response=await fetch(`${import.meta.env.BASE_URL}data/public-radar.json`,{cache:'no-store'});if(!response.ok)throw new Error('公开资料读取失败：'+response.status);const raw=await response.json();validate(raw);publicData=raw;const local=stored();return Response.json({data:compose(publicData,local),revision:local?.revision||0});
  }catch(e){return Response.json({error:e instanceof Error?e.message:String(e)},{status:409})}
}
