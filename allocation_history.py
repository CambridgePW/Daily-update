"""Monthly, point-in-time retrospective allocation illustration. Not historical advice."""
import datetime,json,urllib.request
from pathlib import Path
from urllib.parse import quote
SYMS={'SPY':'SPY','RSP':'RSP','IWM':'IWM','HYG':'HYG','LQD':'LQD','XLY':'XLY','XLP':'XLP','KRE':'KRE','VIX':'^VIX','GLD':'GLD','GDX':'GDX'}
def history(sym):
 url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(sym,safe='')+'?range=11y&interval=1d'
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=22) as f: d=json.load(f)['chart']['result'][0]
 return sorted((datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date(),float(v)) for t,v in zip(d['timestamp'],d['indicators']['quote'][0]['close']) if v is not None)
def before(series,date):
 vals=[v for d,v in series if d<=date]
 return vals[-1] if vals else None
def change(series,date):
 now=before(series,date);old=before(series,date-datetime.timedelta(days=91))
 return (now/old-1)*100 if now and old else None
def run():
 data={k:history(v) for k,v in SYMS.items()}
 today=datetime.datetime.now(datetime.timezone.utc).date()
 months=[];y,m=2016,11
 while (y,m)<=(today.year,today.month):
  target=datetime.date(y,m,1)
  end=(datetime.date(y+1,1,1) if m==12 else datetime.date(y,m+1,1))-datetime.timedelta(days=1)
  end=min(end,today)
  if end>=datetime.date(2016,11,1):
   c={k:change(v,end) for k,v in data.items()}
   vix=before(data['VIX'],end)
   tests={
    'Broad US market trend':c['SPY'] is not None and c['SPY']>0,
    'Market breadth':c['RSP'] is not None and c['SPY'] is not None and c['RSP']>=c['SPY'],
    'Small-cap participation':c['IWM'] is not None and c['SPY'] is not None and c['IWM']>=c['SPY'],
    'Credit risk appetite':c['HYG'] is not None and c['LQD'] is not None and c['HYG']>=c['LQD'],
    'Consumer cyclicals':c['XLY'] is not None and c['XLP'] is not None and c['XLY']>=c['XLP'],
    'Regional banks':c['KRE'] is not None and c['SPY'] is not None and c['KRE']>=c['SPY'],
    'Volatility below 25':vix is not None and vix<25
   }
   valid=sum((c['SPY'] is not None,c['RSP'] is not None and c['SPY'] is not None,c['IWM'] is not None and c['SPY'] is not None,c['HYG'] is not None and c['LQD'] is not None,c['XLY'] is not None and c['XLP'] is not None,c['KRE'] is not None and c['SPY'] is not None,vix is not None))
   if valid==7:
    score=sum(tests.values())
    growth=30+10*score
    months.append({'date':end.isoformat(),'growth':growth,'defensive':100-growth,'positive':score,'tests':7,'spy':round(before(data['SPY'],end),2),'gld':round(before(data['GLD'],end),4) if before(data['GLD'],end) else None,'gdx':round(before(data['GDX'],end),4) if before(data['GDX'],end) else None,'signals':tests})
  m+=1
  if m==13:y,m=y+1,1
 out={'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Retrospective rule-based illustration: 7 equally weighted monthly market tests, each positive test adds 10 percentage points to a 30% growth floor (range 30–100%). Uses only market prices observable at each month end, and 91-day lookbacks. No trading costs, tax, dividends, or rebalancing friction. Not the historical CPW recommendation or an independently validated backtest.','source':'Yahoo Finance daily close history','points':months}
 Path(__file__).with_name('allocation_history.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':run()
