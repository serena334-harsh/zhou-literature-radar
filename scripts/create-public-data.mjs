import {writeFileSync} from 'node:fs';
import {seed} from '../src/data.ts';
const data=structuredClone(seed);
data.schedule='GitHub Actions · 每日 09:00 洛杉矶时间（公开元数据扫描，可能延后）';
data.topics=data.topics.map(t=>({...t,privateAbstract:'',claimBoundary:t.claimBoundary}));
data.reviews=[];
data.reports=[{id:'public-baseline-2026-11-18',checked:'2026-11-18',summary:'首轮公开基线：12 篇文献，含 9 篇外部工作和 3 篇团队公开基线。初始核验以摘要、元数据和版本记录为主，不作为本日新增。公开版自动扫描仅发现元数据候选，实质相近程度仍需人工比较。',sourceChecks:data.papers.map(p=>p.url),failures:['Elsevier 部分原文访问受限；初始资料不是完整系统综述。'],changes:[],baseline:true}];
writeFileSync('public/data/public-radar.json',JSON.stringify(data,null,2)+'\n','utf8');
