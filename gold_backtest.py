"""Historical gold overlay sensitivity test. Research illustration, not investment advice."""
import json,math
from pathlib import Path
P=Path(__file__).with_name('allocation_history.json')
D=json.loads(P.read_text())
pts=D['points']
def stats(rs):
 if not rs:return None
 wealth=peak=1.;drawdown=0.
 for r in rs:
  wealth*=1+r;peak=max(peak,wealth);drawdown=min(drawdown,wealth/peak-1)
 avg=sum(rs)/len(rs)
 vol=math.sqrt(sum((r-avg)**2 for r in rs)/(len(rs)-1)*12) if len(rs)>1 else 0
 return {'months':len(rs),'cumulative_pct':round((wealth-1)*100,2),'annualised_pct':round((wealth**(12/len(rs))-1)*100,2),'volatility_pct':round(vol*100,2),'max_drawdown_pct':round(drawdown*100,2)}
def run():
 points=[p for p in pts if p['date'][:7]<'2026-11' and all(p.get(k) for k in ('spy','gld','gdx'))]
 if len(points)<15:raise ValueError('Insufficient overlapping SPY/GLD/GDX prices')
 growth=70;flags=[False]*3
 rets={str(k):[] for k in (0,5,10,15,25)}
 rets['dynamic']=[]
 allocations=[]
 for i,(a,b) in enumerate(zip(points,points[1:])):
  signal=a['growth']
  if signal<=50 and any(flags):growth=min(70,growth+10);flags=[False]*3
  elif signal>50:
   for j,threshold in enumerate((80,90,100)):
    if signal>=threshold and not flags[j]:growth-=5;flags[j]=True
  eq=b['spy']/a['spy']-1
  bullion=b['gld']/a['gld']-1
  miners=b['gdx']/a['gdx']-1
  for gold in (0,5,10,15,25):
   equity=max(0,growth-gold)
   rets[str(gold)].append(equity/100*eq+gold/100*(.6*bullion+.4*miners))
  # Use only known month-end observations, 3/6/12-month GLD momentum
  # and 6-month GLD versus SPY relative strength.
  gold=0
  if i>=12:
   def mom(k,n):return a[k]/points[i-n][k]-1
   m3,m6,m12=mom('gld',3),mom('gld',6),mom('gld',12)
   relative=(a['gld']/points[i-6]['gld'])/(a['spy']/points[i-6]['spy'])-1
   score=sum((m3>0,m6>0,m12>0,relative>0))
   gold={0:0,1:5,2:10,3:15,4:25}[score]
  # Gold funded from equity allocation, limited by available growth sleeve.
  gold=min(gold,growth)
  equity=growth-gold
  rets['dynamic'].append(equity/100*eq+gold/100*(.6*bullion+.4*miners))
  allocations.append({'date':a['date'],'signal':signal,'contrarian_growth':growth,'gold':gold,'bullion':round(gold*.6,2),'miners':round(gold*.4,2)})
 result={'method':'USD monthly close proxy: SPY, GLD and GDX. Dynamic gold signals: GLD 3-, 6-, 12-month positive momentum plus GLD 6-month relative strength versus SPY; 0/1/2/3/4 positive tests correspond to 0/5/10/15/25% total gold, 60% GLD 40% GDX, funded from growth equities. 12-month warm-up. Signal at month-end applied to NEXT month. Remaining defensive assets assumed 0% return. No dividends, FX, fees, taxes or interest. Not a total-return AUD comparison or an investable recommendation.','start':points[0]['date'],'end':points[-1]['date'],'results':{k:stats(v) for k,v in rets.items()},'latest_dynamic_allocation':allocations[-1],'dynamic_history':allocations}
 Path(__file__).with_name('gold_backtest.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':run()
