"""Discover public metadata candidates; never upload browser notes or infer novelty."""
import argparse
import copy
import datetime as dt
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public/data/public-radar.json'
NS={'a':'http://www.w3.org/2005/Atom','x':'http://arxiv.org/schemas/atom'}
USER_AGENT='ZhouLiteratureRadar/1.0 (+https://github.com/serena334-harsh/zhou-literature-radar)'

def key(value):
    value=re.sub(r'^https?://(?:dx\.)?doi\.org/|^doi:|^arxiv:','',value.strip().lower())
    value=re.sub(r'^https?://arxiv\.org/(?:abs|pdf)/','',value)
    return re.sub(r'v\d+$','',value) if re.match(r'^\d{4}\.\d{4,5}',value) else value

def aliases(p):
    return {key(p.get(k,'')) for k in ('id','doi','arxiv') if p.get(k)}

def direction(text):
    text=text.lower().replace('-', ' ')
    if re.search(r'remote\s+(?:quantum\s+)?state\s+preparation|joint\s+remote\s+preparation|parallel\s+remote\s+preparation',text):
        return '远程态制备 RSP'
    if re.search(r'gate\s+teleportation|teleportation\s+of.{0,35}(?:gate|operation)|quantum\s+operations?\s+teleportation',text) or ('remote implementation' in text and re.search(r'quantum|unitary|operator|operation',text)):
        return '远程量子操作 RIO'
    return None

def candidate(title,authors,family,today):
    return dict(id='',doi='',arxiv='',title=title,zhTitle=title,authors=authors,journal='',direction=family,role='外部文献',stage='待核验',access='见原始来源',readDepth='元数据候选',firstPublished='',updated='',issueDate='',dateNote='自动发现的元数据日期，需对照原始版本；卷期与首发日期分别保留。',discovered=today,verified=today,version='',url='',sourceLabel='',summary='公开元数据自动发现的相关候选。原始摘要与全文尚待人工核对。',focus='公开检索词命中研究方向；请确认具体任务、资源和贡献边界。',boundary='自动收录不代表已精读，不判断稿件实质重叠、抄袭或创新性。',nextAction='打开原始来源，核对摘要、协议属性及与在研课题的具体关系。',priority='建议阅读',dimensions={k:[] for k in ('target','resource','dofs','mechanism','topology')})

def download(url):
    last=None
    for attempt in range(2):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/json, application/atom+xml, text/xml'})
            with urllib.request.urlopen(req,timeout=30) as response:
                return response.read()
        except Exception as exc:
            last=exc
            if attempt==0: time.sleep(3)
    raise RuntimeError(str(last))

def arxiv_entries(raw,today):
    root=ET.fromstring(raw)
    result=[]
    for e in root.findall('a:entry',NS):
        url=e.findtext('a:id','',NS)
        if 'arxiv.org/abs/' not in url: continue
        title=' '.join(e.findtext('a:title','',NS).split())
        summary=' '.join(e.findtext('a:summary','',NS).split())
        family=direction(title) or direction(summary)
        if not family: continue
        arxiv=re.sub(r'v\d+$','',url.rsplit('/',1)[-1])
        authors='; '.join(a.findtext('a:name','',NS) for a in e.findall('a:author',NS))
        p=candidate(title,authors,family,today)
        p.update(id='arxiv:'+arxiv,arxiv=arxiv,doi=e.findtext('x:doi','',NS).strip(),journal=e.findtext('x:journal_ref','',NS).strip() or 'arXiv · quant-ph',firstPublished=e.findtext('a:published','',NS)[:10],updated=e.findtext('a:updated','',NS)[:10],version=(re.search(r'v\d+$',url).group(0) if re.search(r'v\d+$',url) else '版本未注明')+' · 预印本',url='https://arxiv.org/abs/'+arxiv,sourceLabel='arXiv 原始版本元数据（自动候选）')
        result.append(p)
    return result

def date_parts(item,name):
    parts=item.get(name,{}).get('date-parts',[[]])[0]
    return '-'.join(str(x) if i==0 else str(x).zfill(2) for i,x in enumerate(parts[:3]))

def crossref_items(raw,today):
    result=[]
    for item in json.loads(raw).get('message',{}).get('items',[]):
        title=' '.join(item.get('title',[''])[0].split())
        family=direction(title)
        doi=item.get('DOI','').lower()
        if not family or not doi.startswith('10.'): continue
        authors='; '.join(' '.join(filter(None,[a.get('given',''),a.get('family','')])) for a in item.get('author',[]))
        p=candidate(title,authors,family,today)
        online=date_parts(item,'published-online')
        published=date_parts(item,'published')
        p.update(id='doi:'+doi,doi=doi,journal=item.get('container-title',[''])[0],firstPublished=online or published,issueDate=date_parts(item,'published-print'),version='期刊元数据候选',url='https://doi.org/'+doi,sourceLabel='Crossref DOI 元数据（待核验出版社）',dateNote='日期来自 Crossref 注册元数据；首次在线日期需与出版社核验。')
        result.append(p)
    return result

def apply_candidates(data,incoming,today):
    changes=[]
    for item in incoming:
        existing=next((p for p in data['papers'] if aliases(p)&aliases(item)),None)
        if not existing:
            data['papers'].append(item)
            changes.append(dict(paperId=item['id'],kind='首次收录 · 元数据候选',title=item['zhTitle'],before=None,after=copy.deepcopy(item)))
            continue
        before=copy.deepcopy(existing)
        existing['verified']=today
        if item['arxiv'] and existing.get('arxiv')==item['arxiv']:
            old_version=re.search(r'v(\d+)',existing.get('version',''))
            new_version=re.search(r'v(\d+)',item.get('version',''))
            if new_version and (not old_version or int(new_version.group(1))>int(old_version.group(1))):
                existing['version']=item['version']
                existing['updated']=item['updated']
            if item['doi'] and not existing.get('doi'): existing['doi']=item['doi']
        if before.get('version')!=existing.get('version') or before.get('doi')!=existing.get('doi'):
            changes.append(dict(paperId=existing['id'],kind='版本 / 发表元数据变化',title=existing['zhTitle'],before=before,after=copy.deepcopy(existing)))
    return changes

def run(today,filename=DATA):
    data=json.loads(Path(filename).read_text(encoding='utf8'))
    failures=[];checks=[];incoming=[]
    lookback=90 if dt.date.fromisoformat(today).weekday()==0 else 14
    start=(dt.date.fromisoformat(today)-dt.timedelta(days=lookback)).isoformat()
    query='cat:quant-ph AND (all:"remote state preparation" OR all:"remote implementation" OR all:"quantum operations teleportation" OR all:"gate teleportation")'
    url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':query,'sortBy':'lastUpdatedDate','sortOrder':'descending','max_results':80})
    try:
        found=arxiv_entries(download(url),today)
        found=[p for p in found if (p['updated'] or p['firstPublished'])>=start]
        incoming.extend(found);checks.append('arXiv quant-ph 公开术语检索：'+str(len(found))+' 条相关元数据候选；回看 '+str(lookback)+' 天。')
    except Exception as exc: failures.append('arXiv 检索未完成：'+str(exc))
    ids=[p['arxiv'] for p in data['papers'] if p.get('arxiv')]
    if ids:
        time.sleep(3)
        try:
            found=arxiv_entries(download('https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'id_list':','.join(ids[:100]),'max_results':100})),today)
            incoming.extend(found);checks.append('arXiv 已有记录版本核对：'+str(len(found))+' 条。')
        except Exception as exc: failures.append('arXiv 已有版本核对未完成：'+str(exc))
    for term in ['remote state preparation','remote implementation quantum operations','quantum operations teleportation']:
        url='https://api.crossref.org/works?'+urllib.parse.urlencode({'query.title':term,'filter':f'from-pub-date:{start},until-pub-date:{today},type:journal-article','sort':'published','order':'desc','rows':30})
        try:
            found=crossref_items(download(url),today);incoming.extend(found)
            checks.append('Crossref 题名检索 '+term+'：'+str(len(found))+' 条候选；原始摘要待人工核对。')
        except Exception as exc: failures.append('Crossref '+term+' 未完成：'+str(exc))
        time.sleep(1)
    changes=apply_candidates(data,incoming,today)
    report=dict(id='github-scan-'+today,checked=today,summary=f'公开元数据扫描：RSP / RIO 两方向，回看 {lookback} 天；收录或版本信息变化 {len(changes)} 项。新候选尚待人工核验摘要与全文，不作稿件重叠判断。覆盖仅限列出的检索来源。',sourceChecks=checks,failures=failures,changes=changes,baseline=False)
    previous=next((r for r in data['reports'] if r['id']==report['id']),None)
    if previous:
        combined={ (c['paperId'],c['kind']):c for c in previous['changes']+changes }
        report['changes']=list(combined.values())
        report['summary']=f'公开元数据扫描：RSP / RIO 两方向，回看 {lookback} 天；本次条目变化 {len(changes)} 项，本日累计 {len(report["changes"])} 项。自动候选尚待人工核验，不作稿件重叠判断。覆盖仅限列出的检索来源。'
    data['reports']=[report]+[r for r in data['reports'] if r['id']!=report['id']]
    data['reports']=data['reports'][:90]
    data['lastChecked']=today
    data['schedule']='GitHub Actions · 每日 09:00 洛杉矶时间（公开元数据扫描，可能延后）'
    data['reviews']=[]
    for topic in data['topics']: topic['privateAbstract']=''
    Path(filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'date':today,'papers':len(data['papers']),'changes':len(changes),'sourcesCompleted':len(checks),'failures':len(failures)}))
    return len(checks)>0

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--date');args=parser.parse_args()
    run(args.date or dt.datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat())
