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
 # Require complete consecutive monthly observations; omit partial latest month.
 points=[p for p in pts if p['date'][:7]<'2026-11' and all(p.get(k) for k in ('spy','gld','gdx'))]
 if len(points)<12:raise ValueError('Insufficient overlapping SPY/GLD/GDX prices')
 # No look-ahead: allocation determined from month t, applied to t->t+1.
 growth=70;flags=[False]*3;rets={str(k):[] for k in (0,5,10,15,25)}
 for a,b in zip(points,points[1:]):
  g=a['growth']
  if g<=50 and any(flags):growth=min(70,growth+10);flags=[False]*3
  elif g>50:
   for j,threshold in enumerate((80,90,100)):
    if g>=threshold and not flags[j]:growth-=5;flags[j]=True
  eq=b['spy']/a['spy']-1
  bullion=b['gld']/a['gld']-1
  miners=b['gdx']/a['gdx']-1
  for gold in (0,5,10,15,25):
   # Gold overlay funded from growth equities first, split 60% bullion/40% miners.
   # Residual defensive assets earn 0% (not an investable total return).
   equity=max(0,growth-gold)
   cash=100-equity-gold
   if cash<0:raise ValueError('Weights exceed 100%')
   rets[str(gold)].append(equity/100*eq+gold/100*(.6*bullion+.4*miners))
 result={'method':'USD ETF close-to-close proxy, SPY equities, GLD bullion, GDX miners, 60/40 split in gold sleeve; gold funded from growth allocation; other assets earn zero; no dividends, fees, FX, interest, taxes. Allocation from prior month applied to next month. November 2026 partial month excluded. NOT Vanguard benchmark or AUD portfolio returns. Gold exposure is constant sensitivity, not a validated dynamic timing signal.','start':points[0]['date'],'end':points[-1]['date'],'results':{k:stats(v) for k,v in rets.items()}}
 Path(__file__).with_name('gold_backtest.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':run()
