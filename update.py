import csv,io,json,datetime,urllib.request,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
NOW=datetime.datetime.now(datetime.timezone.utc)
SERIES={'US 10Y yield (market proxy)':'DGS10','US 5Y yield (market proxy)':'DGS5','Gold futures USD/oz':'GOLDAMGBD228NLBM','Gold miners ETF (GDX)':'GDX','AUD/USD':'DEXUSAL','US Dollar Index (DXY)':'DTWEXBGS','US real 10Y yield':'DFII10','US unemployment':'UNRATE','US CPI index':'CPIAUCSL','US M2 money stock':'M2SL','US household debt service ratio':'TDSP','Brent crude futures':'DCOILBRENTEU','S&P 500':'SP500','Nasdaq':'NASDAQCOM','VIX':'VIXCLS','High yield corporate bond ETF (HYG)':'HYG','Investment grade corporate bond ETF (LQD)':'LQD','Consumer discretionary ETF (XLY)':'XLY','Consumer staples ETF (XLP)':'XLP','Equal weight S&P ETF (RSP)':'RSP','S&P ETF (SPY)':'SPY','Small cap ETF (IWM)':'IWM','Regional banks ETF (KRE)':'KRE','Broad US banks ETF (KBE)':'KBE','Australian equities ETF (VAS)':'VAS.AX','Australian resources ETF (MVR)':'MVR.AX','Australian quality ETF (AQLT)':'AQLT.AX','Developed markets ETF (VEU)':'VEU','Emerging markets ETF (VWO)':'VWO','Global technology ETF (IXN)':'IXN','Australian government bonds ETF (IAF)':'IAF.AX'}
MARKETS={'S&P 500':'^GSPC','Nasdaq':'^IXIC','VIX':'^VIX','US 10Y yield (market proxy)':'^TNX','US 5Y yield (market proxy)':'^FVX','Gold futures USD/oz':'GC=F','Gold miners ETF (GDX)':'GDX','Brent crude futures':'BZ=F','AUD/USD':'AUDUSD=X','US Dollar Index (DXY)':'DX-Y.NYB','High yield corporate bond ETF (HYG)':'HYG','Investment grade corporate bond ETF (LQD)':'LQD','Consumer discretionary ETF (XLY)':'XLY','Consumer staples ETF (XLP)':'XLP','Equal weight S&P ETF (RSP)':'RSP','S&P ETF (SPY)':'SPY','Small cap ETF (IWM)':'IWM','Regional banks ETF (KRE)':'KRE','Australian equities ETF (VAS)':'VAS.AX','Australian resources ETF (MVR)':'MVR.AX','Australian quality ETF (AQLT)':'AQLT.AX','Developed markets ETF (VEU)':'VEU','Emerging markets ETF (VWO)':'VWO','Global technology ETF (IXN)':'IXN','Australian government bonds ETF (IAF)':'IAF.AX'}
STOOQ={'S&P 500':'^spx','Nasdaq':'^ndq','Gold futures USD/oz':'gc.f','Brent crude futures':'brn.f','AUD/USD':'audusd'}
def trends(obs,name):
 obs=sorted(obs)
 latest=obs[-1][0]
 out={}
 for label,days in [('3m',91),('6m',182),('12m',365)]:
  target=datetime.date.fromisoformat(latest)-datetime.timedelta(days=days)
  choices=[(abs((datetime.date.fromisoformat(d)-target).days),d,v) for d,v in obs if abs((datetime.date.fromisoformat(d)-target).days)<=15]
  if not choices:continue
  _,d,base=min(choices)
  current=obs[-1][1]
  delta=current-base
  is_yield=('yield' in name.lower() or 'spread' in name.lower()) and 'ETF' not in name and 'proxy' not in name.lower()
  out[label]={'value':round(delta*100 if is_yield else delta/base*100,2) if base else None,'unit':'bp' if is_yield else '%','base_date':d}
 return out
def yahoo(item):
 name,symbol=item
 url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?range=1y&interval=1d'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; MarketIntelligence/1.0)','Accept':'application/json'})
  with urllib.request.urlopen(req,timeout=14) as f: doc=json.load(f)
  result=doc['chart']['result'][0]
  timestamps=result.get('timestamp',[])
  closes=result['indicators']['quote'][0]['close']
  volumes=result['indicators']['quote'][0].get('volume',[])
  observations=[(datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),float(v)) for t,v in zip(timestamps,closes) if v is not None]
  if not observations:raise ValueError('No close observations')
  date,value=observations[-1]
  volume_signal=None
  if name in ('S&P 500','Nasdaq') and len(volumes)>=21 and len(observations)>=2 and volumes[-1] is not None:
   recent=[float(z) for z in volumes[-21:-1] if z is not None and z>0]
   if len(recent)>=15 and float(volumes[-1])>0:
    ratio=round(float(volumes[-1])/(sum(recent)/len(recent)),2)
    volume_signal={'ratio_to_20d':ratio,'direction':'down' if value<observations[-2][1] else 'up','note':'Reported index volume; not consolidated exchange volume'}
  return {'name':name,'date':date,'value':round(value,4),'previous':observations[-2][1] if len(observations)>1 else value,'status':'ok','source':url,'unit':'index/market price','trends':trends(observations,name),'volume_signal':volume_signal}
 except Exception as e:
  return {'name':name,'status':'unavailable','error':str(e)[:150],'source':url}
def stooq(item):
 name,symbol=item
 url='https://stooq.com/q/d/l/?s='+quote(symbol)+'&i=d&d1=20251001'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=14) as f: rows=list(csv.DictReader(io.StringIO(f.read().decode('utf-8-sig'))))
  obs=[(x['Date'],float(x['Close'])) for x in rows if x.get('Close') not in ('',None,'N/D')]
  if not obs:raise ValueError('No prices')
  date,value=obs[-1]
  return {'name':name,'date':date,'value':round(value,4),'previous':obs[-2][1] if len(obs)>1 else value,'status':'ok','source':url,'unit':'market price','trends':trends(obs,name)}
 except Exception as e:return {'name':name,'status':'unavailable','error':str(e)[:150],'source':url}
def bls_unemployment():
 url='https://api.bls.gov/publicAPI/v1/timeseries/data/LNS14000000'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'CambridgeMarketIntelligence/1.0','Accept':'application/json'})
  with urllib.request.urlopen(req,timeout=16) as f:doc=json.load(f)
  if doc.get('status')!='REQUEST_SUCCEEDED':raise ValueError(str(doc.get('message')))
  points=[]
  for row in doc['Results']['series'][0]['data']:
   if row.get('period','').startswith('M') and row['period']!='M13':
    try:points.append((row['year']+'-'+row['period'][1:]+'-01',float(row['value'])))
    except (ValueError,TypeError):continue
  points.sort()
  if not points:raise ValueError('No monthly observations')
  date,value=points[-1]
  return {'name':'US unemployment','date':date,'value':value,'previous':points[-2][1] if len(points)>1 else value,'status':'ok','source':url,'unit':'%','trends':trends(points,'US unemployment')}
 except Exception as e:return {'name':'US unemployment','status':'unavailable','error':'BLS: '+str(e)[:130],'source':url}
def treasury_real_yield():
 year=NOW.year
 url='https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/'+str(year)+'/all?type=daily_treasury_real_yield_curve&field_tdr_date_value='+str(year)+'&page&_format=csv'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/csv'})
  with urllib.request.urlopen(req,timeout=18) as f:
   rows=list(csv.DictReader(io.StringIO(f.read().decode('utf-8-sig'))))
  observations=[]
  for row in rows:
   try:
    date=datetime.datetime.strptime(row['Date'].strip(),'%m/%d/%Y').date().isoformat()
    value=float(row['10 YR'])
    observations.append((date,value))
   except (KeyError,ValueError,TypeError):continue
  observations.sort()
  if not observations:raise ValueError('Treasury CSV returned no usable 10-year real yields')
  date,value=observations[-1]
  return {'name':'US real 10Y yield','date':date,'value':value,'previous':observations[-2][1] if len(observations)>1 else value,'status':'ok','unit':'%','source':url,'trends':trends(observations,'US real 10Y yield')}
 except Exception as e:return {'name':'US real 10Y yield','status':'unavailable','error':'Treasury: '+str(e)[:130],'source':url}
def fetch(item):
 name,code=item
 if name=='US unemployment':return bls_unemployment()
 if name=='US real 10Y yield':return treasury_real_yield()
 if name in MARKETS:
  primary=yahoo((name,MARKETS[name]))
  if primary['status']=='ok':return primary
  if name in STOOQ:
   secondary=stooq((name,STOOQ[name]))
   if secondary['status']=='ok':return secondary
   primary['error']+='; Stooq: '+secondary.get('error','')
  return primary
 url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+quote(code)+'&cosd=2024-01-01'
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=8) as f: rows=list(csv.reader(io.StringIO(f.read().decode('utf-8-sig'))))
  obs=[]
  for row in rows[1:]:
   try:obs.append((row[0],float(row[1])))
   except (ValueError,IndexError):pass
  if not obs:raise ValueError('No observations')
  date,value=obs[-1]
  return {'name':name,'date':date,'value':value,'previous':obs[-2][1] if len(obs)>1 else value,'status':'ok','source':url,'trends':trends(obs,name)}
 except Exception as e:return {'name':name,'status':'unavailable','error':str(e)[:150],'source':url}
def news(item):
 category,term=item;url='https://news.google.com/rss/search?q='+quote(term)+'&hl=en-AU&gl=AU&ceid=AU:en'
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as f:root=ET.fromstring(f.read())
  return [{'category':category,'title':x.findtext('title'),'url':x.findtext('link'),'published':x.findtext('pubDate')} for x in root.findall('.//item')[:5]]
 except Exception:return []
# ASX price-trend research watchlist; independent of broker consensus.
# These signals never claim to be analyst recommendations.
ASX_WATCH={
'CSL':('Healthcare','Defensive'),'SHL':('Healthcare','Defensive'),'WOW':('Consumer staples','Defensive'),'COL':('Consumer staples','Defensive'),
'TLS':('Telecommunications','Defensive'),'TCL':('Infrastructure','Defensive'),
'BHP':('Resources','Cyclical'),'RIO':('Resources','Cyclical'),'WES':('Consumer','Cyclical'),'QBE':('Insurance','Cyclical'),
'GMG':('Property','Growth'),'NWL':('Financial technology','Growth'),'TLX':('Healthcare','Growth'),'XRO':('Technology','Growth'),
'PRU':('Gold miners','Cyclical'),'NST':('Gold miners','Cyclical')}
def asx_trend(item):
 symbol,(sector,style)=item
 result=yahoo(('ASX '+symbol,symbol+'.AX'))
 return {'symbol':symbol,'sector':sector,'style':style,'status':result.get('status'),'date':result.get('date'),'price':result.get('value'),'trends':result.get('trends',{}),'source':result.get('source')}
with ThreadPoolExecutor(max_workers=10) as pool:
 readings=list(pool.map(fetch,SERIES.items()))
 asx_watch=list(pool.map(asx_trend,ASX_WATCH.items()))
 headlines=list(pool.map(news,[('Central banks','RBA Federal Reserve rates policy'),('Credit','bank defaults delinquencies credit stress'),('Geopolitics','geopolitics war tariffs Reuters'),('Gold','gold price central bank purchases')]))
try:
 old={x['name']:x for x in json.loads(Path(__file__).with_name('daily.json').read_text()).get('readings',[]) if x.get('value') is not None}
except (OSError,ValueError):old={}
for i,x in enumerate(readings):
 if x.get('status')!='ok' and x['name'] in old:
  readings[i]={**old[x['name']],'status':'last_known','error':x.get('error','Feed unavailable')}
# Explicitly labelled, transparent market proxies. These are NOT official macro statistics.
market={x['name']:x for x in readings if x.get('status')=='ok'}
def relative_proxy(name,a,b,explanation):
 x,y=market.get(a),market.get(b)
 if not x or not y:return
 changes={}
 for term in ('3m','6m','12m'):
  tx=x.get('trends',{}).get(term)
  ty=y.get('trends',{}).get(term)
  if tx and ty and tx.get('value') is not None and ty.get('value') is not None:
   changes[term]={'value':round(tx['value']-ty['value'],2),'unit':'pp','base_date':tx.get('base_date')}
 if not changes:return
 readings.append({'name':name,'date':min(x['date'],y['date']),'value':changes.get('3m',{}).get('value'),'status':'ok','unit':'3m relative return (pp)','trends':changes,'source':x['source'],'note':explanation,'proxy':True})
relative_proxy('Credit risk appetite proxy (HYG vs LQD)','High yield corporate bond ETF (HYG)','Investment grade corporate bond ETF (LQD)','Relative ETF returns; not an option-adjusted credit spread. Interest-rate sensitivity also affects prices.')
relative_proxy('Consumer demand proxy (XLY vs XLP)','Consumer discretionary ETF (XLY)','Consumer staples ETF (XLP)','Relative stock-sector performance; not a consumer-confidence survey.')
relative_proxy('Market breadth proxy (RSP vs SPY)','Equal weight S&P ETF (RSP)','S&P ETF (SPY)','Relative ETF returns; not an advance-decline breadth statistic.')
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
regime='DATA INSUFFICIENT' if count<3 else 'DEFENSIVE' if avg<=-.6 else 'CONSTRUCTIVE' if avg>=.6 else 'MIXED / CAUTIOUS'
positioning={} if count<3 else {'Equities':'REDUCE / DEFENSIVE' if avg<=-.6 else 'SELECTIVE BUY' if avg>=.6 else 'HOLD / SELECTIVE','Government bonds':'HOLD / REVIEW YIELDS','Gold':'HOLD / REVIEW REAL YIELDS','Cash':'MAINTAIN BUFFER' if avg<.6 else 'NORMAL BUFFER'}
output={'generated_at_utc':NOW.isoformat(),'regime':regime,'score':round(avg,2) if avg is not None else None,'coverage':count,'positioning':positioning,'indicators':notes,'readings':readings,'asx_watch':asx_watch,'news':[n for group in headlines for n in group]}
Path(__file__).with_name('daily.json').write_text(json.dumps(output,indent=2))
print('Saved daily.json:',regime,'coverage',count)
