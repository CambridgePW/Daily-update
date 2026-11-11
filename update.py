import csv,io,json,datetime,urllib.request,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
NOW=datetime.datetime.now(datetime.timezone.utc)
SERIES={'US 10Y yield (market proxy)':'DGS10','US 5Y yield (market proxy)':'DGS5','Gold futures USD/oz':'GOLDAMGBD228NLBM','AUD/USD':'DEXUSAL','USD index futures':'DTWEXBGS','US real 10Y yield':'DFII10','High yield spread':'BAMLH0A0HYM2','Investment grade spread':'BAMLC0A0CM','US unemployment':'UNRATE','Consumer sentiment':'UMCSENT','All loan delinquencies':'DRALACBS','Credit card delinquencies':'DRCCLACBS','Brent crude futures':'DCOILBRENTEU','S&P 500':'SP500','Nasdaq':'NASDAQCOM','VIX':'VIXCLS','Australia interbank rate (not RBA cash rate)':'IR3TIB01AUM156N'}
MARKETS={'S&P 500':'^GSPC','Nasdaq':'^IXIC','VIX':'^VIX','US 10Y yield (market proxy)':'^TNX','US 5Y yield (market proxy)':'^FVX','Gold futures USD/oz':'GC=F','Brent crude futures':'BZ=F','AUD/USD':'AUDUSD=X','USD index futures':'DX=F'}
STOOQ={'S&P 500':'^spx','Nasdaq':'^ndq','Gold futures USD/oz':'gc.f','Brent crude futures':'brn.f','AUD/USD':'audusd'}
def yahoo(item):
 name,symbol=item
 url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?range=10d&interval=1d'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; MarketIntelligence/1.0)','Accept':'application/json'})
  with urllib.request.urlopen(req,timeout=14) as f: doc=json.load(f)
  result=doc['chart']['result'][0]
  timestamps=result.get('timestamp',[])
  closes=result['indicators']['quote'][0]['close']
  observations=[(datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),float(v)) for t,v in zip(timestamps,closes) if v is not None]
  if not observations:raise ValueError('No close observations')
  date,value=observations[-1]
  return {'name':name,'date':date,'value':round(value,4),'previous':observations[-2][1] if len(observations)>1 else value,'status':'ok','source':url,'unit':'index/market price'}
 except Exception as e:
  return {'name':name,'status':'unavailable','error':str(e)[:150],'source':url}
def stooq(item):
 name,symbol=item
 url='https://stooq.com/q/d/l/?s='+quote(symbol)+'&i=d&d1=20261001'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=14) as f: rows=list(csv.DictReader(io.StringIO(f.read().decode('utf-8-sig'))))
  obs=[(x['Date'],float(x['Close'])) for x in rows if x.get('Close') not in ('',None,'N/D')]
  if not obs:raise ValueError('No prices')
  date,value=obs[-1]
  return {'name':name,'date':date,'value':round(value,4),'previous':obs[-2][1] if len(obs)>1 else value,'status':'ok','source':url,'unit':'market price'}
 except Exception as e:return {'name':name,'status':'unavailable','error':str(e)[:150],'source':url}
def fetch(item):
 name,code=item
 if name in MARKETS:
  primary=yahoo((name,MARKETS[name]))
  if primary['status']=='ok':return primary
  if name in STOOQ:
   secondary=stooq((name,STOOQ[name]))
   if secondary['status']=='ok':return secondary
   primary['error']+='; Stooq: '+secondary.get('error','')
  return primary
 url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+quote(code)+'&cosd=2026-01-01'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=8) as f: rows=list(csv.reader(io.StringIO(f.read().decode('utf-8-sig'))))
  obs=[]
  for row in rows[1:]:
   try:obs.append((row[0],float(row[1])))
   except (ValueError,IndexError):pass
  if not obs:raise ValueError('No observations')
  date,value=obs[-1]
  return {'name':name,'date':date,'value':value,'previous':obs[-2][1] if len(obs)>1 else value,'status':'ok','source':url}
 except Exception as e:return {'name':name,'status':'unavailable','error':str(e)[:150],'source':url}
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
 if (NOW.date()-datetime.date.fromisoformat(x['date'])).days>(5 if k in MARKETS else 100):return None
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
