"""Refresh ASX broker-consensus research from an authorised JSON feed.

Set BROKER_CONSENSUS_URL and (if required) BROKER_CONSENSUS_TOKEN as GitHub
Actions secrets. Do not point this at a website intended for human browsing.
Feed schema: {"as_of":"YYYY-MM-DD","stocks":[{"symbol":"CSL",
"sector":"Healthcare","style":"defensive","buy":5,"hold":2,"sell":0,
"target":300.0,"price":280.0,"rating_updated":"YYYY-MM-DD"}]}.
Only publish data that the provider permits to be displayed publicly.
"""
import json,os,urllib.request,datetime,pathlib
P=pathlib.Path("broker_consensus.json")
today=datetime.datetime.now(datetime.timezone.utc).date()
url=os.getenv("BROKER_CONSENSUS_URL","").strip()
if not url:
    print("No licensed broker feed configured; leaving existing snapshot untouched.")
    raise SystemExit(0)
if not url.startswith("https://"):
    raise SystemExit("Broker feed URL must use HTTPS")
headers={"Accept":"application/json","User-Agent":"CPW-research-dashboard/1.0"}
if os.getenv("BROKER_CONSENSUS_TOKEN"):
    headers["Authorization"]="Bearer "+os.environ["BROKER_CONSENSUS_TOKEN"]
with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=25) as res:
    raw=json.load(res)
if not isinstance(raw,dict) or not isinstance(raw.get("stocks"),list):
    raise SystemExit("Invalid broker feed schema")
date=datetime.date.fromisoformat(raw["as_of"][:10])
if not 0 <= (today-date).days <= 7:
    raise SystemExit("Broker feed out of date; no update published")
stocks=[]
for x in raw["stocks"]:
    try:
        symbol=str(x["symbol"]).upper().replace(".AX","")
        if not symbol.isalnum() or len(symbol)>6: continue
        b,h,se=[int(x[k]) for k in ("buy","hold","sell")]
        n=b+h+se
        if min(b,h,se)<0 or n<1: continue
        updated=datetime.date.fromisoformat(x["rating_updated"][:10])
        if not 0 <= (today-updated).days <= 90: continue
        score=(3*b+2*h+se)/n
        rating="Strong Buy" if score>=2.70 else "Buy" if score>=2.31 else "Hold" if score>=1.81 else "Sell" if score>=1.50 else "Strong Sell"
        target=float(x["target"]) if x.get("target") is not None else None
        price=float(x["price"]) if x.get("price") is not None else None
        upside=round((target/price-1)*100,1) if target is not None and price and price>0 else None
        stocks.append(dict(symbol=symbol,sector=str(x.get("sector",""))[:50],style=str(x.get("style",""))[:30],buy=b,hold=h,sell=se,brokers=n,score=round(score,2),rating=rating,upside=upside,rating_updated=updated.isoformat()))
    except (KeyError,TypeError,ValueError,OverflowError):
        continue
stocks.sort(key=lambda x:(x["brokers"]>=3 and x["score"]>=2.31 and (x["upside"] is None or x["upside"]>=5),x["score"],x["brokers"]),reverse=True)
output={"status":"ok" if stocks else "unavailable","as_of":date.isoformat(),"provider":str(raw.get("provider","Licensed broker data feed"))[:90],"stocks":stocks,"method":"Fresh ratings <=90 days; 3+ brokers for shortlist; Buy consensus and >=5% target upside when supplied."}
P.write_text(json.dumps(output,indent=2)+"\n")
print("Published",len(stocks),"covered ASX symbols")
