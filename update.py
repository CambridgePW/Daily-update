import csv,io,json,datetime,urllib.request,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
NOW=datetime.datetime.now(datetime.timezone.utc)
SERIES={'US 10Y yield':'DGS10','US 2Y yield':'DGS2','US real 10Y yield':'DFII10','High yield spread':'BAMLH0A0HYM2','Investment grade spread':'BAMLC0A0CM','US unemployment':'UNRATE','Consumer sentiment':'UMCSENT','All loan delinquencies':'DRALACBS','Credit card delinquencies':'DRCCLACBS','Brent oil':'DCOILBRENTEU','S&P 500':'SP500','Nasdaq':'NASDAQCOM','VIX':'VIXCLS','Broad USD (not DXY)':'DTWEXBGS','Australia interbank rate (not RBA cash rate)':'IR3TIB01AUM156N'}
def fetch(item):
 name,code=item
 urls=[
  'https://api.db.nomics.world/v22/series/FRED/'+quote(code)+'?observations=1',
  'https://fred.stlouisfed.org/graph/fredgraph.csv?id='+quote(code)+'&cosd=2025-01-01&coed='+NOW.date().isoformat()
 ]
 errors=[]
 for url in urls:
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/csv'})
   with urllib.request.urlopen(req,timeout=12) as f: raw=f.read().decode('utf-8-sig')
   if 'db.nomics' in url:
    series=json.loads(raw)['series']['docs'][0]
    observations=[(date,float(value)) for date,value in zip(series['period'],series['value']) if value not in ('NA',None,'')]
   else:
    rows=list(csv.reader(io.StringIO(raw)))
    observations=[]
    for row in rows[1:]:
     try:observations.append((row[0],float(row[1])))
     except (ValueError,IndexError):pass
   if not observations:raise ValueError('No numeric observations')
   date,value=observations[-1];prior=observations[-2][1] if len(observations)>1 else value
   return {'name':name,'date':date,'value':value,'previous':prior,'status':'ok','source':url}
  except Exception as e:errors.append(str(e)[:100])
 return {'name':name,'status':'unavailable','error':'; '.join(errors),'source':urls[0]}
def news(item):
 category,term=item;url='https://news.google.com/rss/search?q='+quote(term)+'&hl=en-AU&gl=AU&ceid=AU:en'
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as f:root=ET.fromstring(f.read())
  return [{'category':category,'title':x.findtext('title'),'url':x.findtext('link'),'published':x.findtext('pubDate')} for x in root.findall('.//item')[:5]]
 except Exception:return []
with ThreadPoolExecutor(max_workers=10) as pool:
 readings=list(pool.map(fetch,SERIES.items()))
 headlines=list(pool.map(news,[('Central banks','RBA Federal Reserve rates policy'),('Credit','bank defaults delinquencies credit stress'),('Geopolitics','geopolitics war tariffs Reuters'),('Gold','gold price central bank purchases')]))
r={x['name']:x for x in readings}
def v(k):
 x=r.get(k,{})
 if x.get('status')!='ok':return None
 if (NOW.date()-datetime.date.fromisoformat(x['date'])).days>100:return None
 return x['value']
score=0;count=0;notes=[]
def add(label,n):
 global score,count
 score+=n;count+=1;notes.append({'name':label,'score':n})
hy=v('High yield spread')
if hy is not None:add('Credit risk',-2 if hy>=6 else -1 if hy>=4.5 else 1 if hy<3.5 else 0)
vix=v('VIX')
if vix is not None:add('Volatility',-2 if vix>=30 else -1 if vix>=22 else 1 if vix<17 else 0)
un=v('US unemployment')
if un is not None:add('Employment',-1 if un>=5.5 else 1 if un<4.2 else 0)
sent=v('Consumer sentiment')
if sent is not None:add('Consumer confidence',-1 if sent<60 else 1 if sent>80 else 0)
delinq=v('All loan delinquencies')
if delinq is not None:add('Loan stress',-1 if delinq>3 else 1 if delinq<2 else 0)
avg=score/count if count else None
regime='DATA INSUFFICIENT' if avg is None else 'DEFENSIVE' if avg<=-.6 else 'CONSTRUCTIVE' if avg>=.6 else 'MIXED / CAUTIOUS'
positioning={} if avg is None else {'Equities':'REDUCE / DEFENSIVE' if avg<=-.6 else 'SELECTIVE BUY' if avg>=.6 else 'HOLD / SELECTIVE','Government bonds':'HOLD / REVIEW YIELDS','Gold':'HOLD / REVIEW REAL YIELDS','Cash':'MAINTAIN BUFFER' if avg<.6 else 'NORMAL BUFFER'}
output={'generated_at_utc':NOW.isoformat(),'regime':regime,'score':round(avg,2) if avg is not None else None,'coverage':count,'positioning':positioning,'indicators':notes,'readings':readings,'news':[n for group in headlines for n in group]}
Path(__file__).with_name('daily.json').write_text(json.dumps(output,indent=2))
print('Saved daily.json:',regime,'coverage',count)
