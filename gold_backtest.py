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
    strategies=('no_gold','momentum_only','momentum_contrarian','separate_sleeves')
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
        # Independently score bullion and miners; limit each to 15%, combined to 25%.
        # Miners require stronger relative trend than bullion; controlled pullbacks
        # can earn 5% when long-term support remains. No future data used.
        bullion_score=int(g12>0)+int(g6>0)+int(g3>0)
        bullion_weight=(0,5,10,15)[bullion_score]
        if g12>0 and g6>0 and -12<g3<0:
            bullion_weight=min(15,bullion_weight+5)
        relative3=(a['gdx']/points[i-3]['gdx'])/(a['gld']/points[i-3]['gld'])-1
        relative6=(a['gdx']/points[i-6]['gdx'])/(a['gld']/points[i-6]['gld'])-1
        miner_score=int(m12>0)+int(m6>0)+int(m3>0)+int(relative3>0)+int(relative6>0)
        miner_weight=(0,0,5,10,15,15)[miner_score]
        if m12>0 and relative6>0 and -20<m3<0:
            miner_weight=min(15,miner_weight+5)
        if bullion_weight+miner_weight>25:
            # Preserve defensive bullion allocation before higher-beta miners.
            miner_weight=25-bullion_weight
        growth=min(70,max(0,a['growth']))
        next_spy=b['spy']/a['spy']-1
        next_gld=b['gld']/a['gld']-1
        next_gdx=b['gdx']/a['gdx']-1
        for name,w in [('no_gold',0),('momentum_only',momentum_weight),('momentum_contrarian',contrarian_weight),('separate_sleeves',bullion_weight+miner_weight)]:
            w=min(w,growth)
            # 40% miners, 60% bullion; defensive sleeve zero return (limitation).
            ret=(growth-w)/100*next_spy+(bullion_weight/100*next_gld+miner_weight/100*next_gdx if name=='separate_sleeves' else w/100*(.6*next_gld+.4*next_gdx))
            results[name].append(ret)
        rows.append({'date':a['date'],'next_date':b['date'],'growth_pct':growth,
                     'momentum_gold_pct':momentum_weight,'contrarian_gold_pct':contrarian_weight,
                     'contrarian_bullion_pct':round(contrarian_weight*.6,2),
                     'contrarian_miners_pct':round(contrarian_weight*.4,2),
                     'gold_3m_pct':round(g3,2),'gold_6m_pct':round(g6,2),'gold_12m_pct':round(g12,2),
                     'gdx_3m_pct':round(m3,2),'gdx_6m_pct':round(m6,2),'gdx_12m_pct':round(m12,2),
                     'contrarian_bonus_pct':bonus,'separate_bullion_pct':bullion_weight,'separate_miners_pct':miner_weight,'separate_total_pct':bullion_weight+miner_weight,'miners_vs_bullion_3m_pct':round(relative3*100,2)})
    if not rows:raise ValueError('No backtest observations from 2016 onward')
    windows={}
    for n in (3,6,12,36,60,120):
        windows[str(n)+'m']={k:stats(v[-n:]) if len(v)>=n else None for k,v in results.items()}
    output={'generated_from':data.get('generated_at_utc'),'start':rows[0]['date'],'end':rows[-1]['next_date'],
        'method':'Four strategies including independent bullion (0-15%) and miner (0-15%) signals, combined maximum 25%. Bullion uses GLD 3/6/12-month momentum plus controlled correction; miners use GDX 3/6/12-month momentum and GDX/GLD relative strength plus controlled correction. These rules are research hypotheses, not optimised or approved. Point-in-time monthly signal at month-end, returns NEXT month. SPY/GLD/GDX adjusted-price USD proxies; growth allocation from seven market signals. Gold overlay 60% bullion GLD / 40% miners GDX funded from equities. Contrarian adds 5 percentage points for controlled three-month correction while 6- and 12-month bullion and 12-month miners trends remain positive. Does NOT include real yields, DXY, Australian currency, bond/cash returns, costs, tax or portfolio-level distributions. Not the live four-factor model; do not treat as validated investable returns.',
        'results':{k:stats(v) for k,v in results.items()},'windows':windows,'latest_dynamic_allocation':rows[-1],'dynamic_history':rows}
    Path(__file__).with_name('gold_backtest.json').write_text(json.dumps(output,indent=2))
if __name__=='__main__':run()
