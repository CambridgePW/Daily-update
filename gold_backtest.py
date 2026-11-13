"""Point-in-time monthly gold overlay research, 2016 onward. No hindsight optimisation."""
import json, math
from pathlib import Path
P=Path(__file__).with_name('allocation_history.json')
def stats(rs):
    if not rs:return None
    wealth=peak=1.; dd=0.
    for r in rs:
        wealth*=1+r; peak=max(peak,wealth);dd=min(dd,wealth/peak-1)
    mean=sum(rs)/len(rs)
    vol=math.sqrt(sum((r-mean)**2 for r in rs)/(len(rs)-1)*12) if len(rs)>1 else 0
    return {'months':len(rs),'cumulative_pct':round((wealth-1)*100,2),'annualised_pct':round((wealth**(12/len(rs))-1)*100,2),'volatility_pct':round(vol*100,2),'max_drawdown_pct':round(dd*100,2)}
def run():
    data=json.loads(P.read_text())
    points=[p for p in data['points'] if p.get('spy') and p.get('gld') and p.get('gdx')]
    if len(points)<36:raise ValueError('Need at least 36 monthly points including 12-month warm-up')
    strategies=('no_gold','momentum_only','momentum_contrarian')
    results={k:[] for k in strategies}
    rows=[]
    for i in range(12,len(points)-1):
        a,b=points[i],points[i+1]
        if a['date']<'2016-01-01':continue
        def momentum(ticker,n):return 100*(a[ticker]/points[i-n][ticker]-1)
        g3,g6,g12=(momentum('gld',n) for n in (3,6,12))
        m3,m6,m12=(momentum('gdx',n) for n in (3,6,12))
        # Price-only proxies: long-term positive trend and a controlled correction.
        # Macro real-yield/DXY series not included: these are NOT identical to live model.
        positive=sum((g3>0,g6>0,g12>0,m3>0,m12>0))
        momentum_weight={0:0,1:5,2:10,3:15,4:20,5:20}[positive]
        long_support=int(g12>0)+int(m12>0)
        correction=(g3<0 or m3<0) and g3>-18 and m3>-30
        bonus=5 if correction and long_support==2 and g6>0 else 0
        contrarian_weight=min(25,momentum_weight+bonus)
        growth=min(70,max(0,a['growth']))
        next_spy=b['spy']/a['spy']-1
        next_gld=b['gld']/a['gld']-1
        next_gdx=b['gdx']/a['gdx']-1
        for name,w in [('no_gold',0),('momentum_only',momentum_weight),('momentum_contrarian',contrarian_weight)]:
            w=min(w,growth)
            # 40% miners, 60% bullion; defensive sleeve zero return (limitation).
            ret=(growth-w)/100*next_spy+w/100*(.6*next_gld+.4*next_gdx)
            results[name].append(ret)
        rows.append({'date':a['date'],'next_date':b['date'],'growth_pct':growth,
                     'momentum_gold_pct':momentum_weight,'contrarian_gold_pct':contrarian_weight,
                     'contrarian_bullion_pct':round(contrarian_weight*.6,2),
                     'contrarian_miners_pct':round(contrarian_weight*.4,2),
                     'gold_3m_pct':round(g3,2),'gold_6m_pct':round(g6,2),'gold_12m_pct':round(g12,2),
                     'gdx_3m_pct':round(m3,2),'gdx_6m_pct':round(m6,2),'gdx_12m_pct':round(m12,2),
                     'contrarian_bonus_pct':bonus})
    if not rows:raise ValueError('No backtest observations from 2016 onward')
    windows={}
    for n in (3,6,12,36,60,120):
        windows[str(n)+'m']={k:stats(v[-n:]) if len(v)>=n else None for k,v in results.items()}
    output={'generated_from':data.get('generated_at_utc'),'start':rows[0]['date'],'end':rows[-1]['next_date'],
        'method':'Point-in-time monthly signal at month-end, returns NEXT month. SPY/GLD/GDX adjusted-price USD proxies; growth allocation from seven market signals. Gold overlay 60% bullion GLD / 40% miners GDX funded from equities. Contrarian adds 5 percentage points for controlled three-month correction while 6- and 12-month bullion and 12-month miners trends remain positive. Does NOT include real yields, DXY, Australian currency, bond/cash returns, costs, tax or portfolio-level distributions. Not the live four-factor model; do not treat as validated investable returns.',
        'results':{k:stats(v) for k,v in results.items()},'windows':windows,'latest_dynamic_allocation':rows[-1],'dynamic_history':rows}
    Path(__file__).with_name('gold_backtest.json').write_text(json.dumps(output,indent=2))
if __name__=='__main__':run()
