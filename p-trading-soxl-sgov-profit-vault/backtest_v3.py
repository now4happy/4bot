#!/usr/bin/env python3
"""판 3 — P매매 SOXL 30% 수익 분리(현금만 인출, 실현 기준, Q6: 매도 수량 = 새 배수×표 수량) vs 인출 없음.
사용: python3 -I backtest_v3.py <p_data_v9.json> <sgov_close.csv> <sgov_dist.csv> <outdir>
계좌 = 현금 k + 표 따라가는 보유(qT, 원가 CBT) + 초과 보유(qE, 원가 CBE).
 - 표 순매수일: 표 매수 수량 × 매수 배수(mb)를 표 평균 체결단가로 매수(현금 모자라면 가능한 만큼).
 - 표 순매도일: 표 매도 수량 × mb 를 같은 단가로 매도. 보유(qT)보다 많으면 보유만큼만(cap_sells와 같은 결과).
   → fanding_trade.py raw_lines(표 수량×배수)·cap_sells 동작과 같음. 초과 보유는 매도줄로 팔리지 않는다.
 - 분리: 실현 순수익 G ≥ T×30% 를 표일에 감지 → 다음 표일 G 전액 현금 인출·SGOV 매수, mb = T÷(10000+시즌실현수익).
   그 순간 qT 중 새 배수×표 보유를 넘는 수량을 초과 보유(qE)로 옮긴다(원가는 그 시점 평균원가).
 - 초과 보유 해소(excess_rule):
     flat  = 표 보유가 0이 된 표일을 확인한 다음 표일 종가에 초과 보유 전량을 별도 매도  ← 본 계산
     reset = 시즌 리셋(새 시즌 첫 행) 종가에 전량 매도
     hold  = 팔지 않고 자료 끝까지 보유
"""
import json,csv,sys,os,datetime as dt
T=10000.0
FIX={'2025-11-29':'2025-11-28'}
def load(v9p,sgp,sdp):
    rows=[r for r in json.load(open(v9p)) if r['잔금'] is not None and r['현재보유개수'] is not None]
    for r in rows: r['d']=FIX.get(r['종가일'],r['종가일'])
    sg={r['date']:float(r['close']) for r in csv.DictReader(open(sgp))}
    sd=[(r['ex_date'],float(r['amount'])) for r in csv.DictReader(open(sdp))]
    return rows,sg,sd
def run(rows,sg,sd,X=None,reset='compound',fee=0.0,sec=0.0,wht=0.15,excess_rule='flat'):
    r0=rows[0]
    mb=1.0; k=r0['잔금']; qT=float(r0['현재보유개수']); CBT=qT*(r0['보유평단'] or 0.0); qE=0.0; CBE=0.0; G=r0['시즌실현수익']
    lots=[]; dist=0.0; armed=False; sell_E=False; seps=[]; exs=[]; series=[]; cost_tab=cost_sep=cost_ex=0.0; short=[]; capped=[]; yr={}; sdi=0
    while sdi<len(sd) and sd[sdi][0]<=r0['d']: sdi+=1
    e0=k+qT*r0['종가']; series.append((r0['d'],r0['종가'],e0,0.0,e0,mb,qT,qE,k))
    for a,b in zip(rows,rows[1:]):
        d=b['d']; P=b['종가']; y=d[:4]; yr.setdefault(y,0.0); new_season=a['시즌']!=b['시즌']
        if new_season:
            mb=(T+G)/10000.0 if reset=='compound' else T/10000.0
        else:
            dh=b['현재보유개수']-a['현재보유개수']; dc=b['잔금']-a['잔금']; h0=a['현재보유개수']; dR=b['시즌실현수익']-a['시즌실현수익']
            if dh>0 and dc<0:
                px=-dc/dh; want=mb*dh
                if want*px*(1+fee)>k+1e-9:
                    got=max(k,0.0)/(px*(1+fee)); short.append((d,want-got,want)); want=got
                f=want*px*fee; k-=want*px+f; qT+=want; CBT+=want*px; G-=f; cost_tab+=f; yr[y]-=f
                ex=(want/dh)*dR; CBT+=ex; G+=ex; yr[y]+=ex           # 혼합 체결일: 표 실현수익 변화 반영
            elif dh<0 and dc>0:
                px=dc/(-dh); want=mb*(-dh); sold=min(qT,want)
                if sold<want-1e-9: capped.append((d,want-sold,want))
                if sold>0:
                    proceeds=sold*px; f=proceeds*(fee+sec); cst=CBT*(sold/qT); rz=proceeds-cst
                    CBT-=cst; qT-=sold; k+=proceeds-f; G+=rz-f; cost_tab+=f; yr[y]+=rz-f
                    ex=(sold/(-dh))*(dR-(dc-(-dh)*(a['보유평단'] or 0.0)))
                    if b['현재보유개수']>0 and qT>1e-9: CBT+=ex; G+=ex; yr[y]+=ex
            elif dh==0 and abs(dc)>1e-9:
                ratio=(qT/h0) if h0 else mb; k+=ratio*dc; CBT+=ratio*(dc-dR); G+=ratio*dR; yr[y]+=ratio*dR
            if qT<1e-9: qT=0.0; CBT=0.0
            if b['현재보유개수']==0 and qT>0:      # 표는 0인데 남은 수량 → 초과 보유로
                qE+=qT; CBE+=CBT; qT=0.0; CBT=0.0
        # 초과 보유 별도 매도
        do=(excess_rule=='flat' and sell_E) or (excess_rule=='reset' and new_season)
        if do and qE>0:
            proceeds=qE*P; f=proceeds*(fee+sec); rz=proceeds-CBE
            exs.append(dict(date=d,shares=qE,price=P,proceeds=proceeds,realized=rz,cost=f))
            k+=proceeds-f; G+=rz-f; cost_ex+=f; yr[y]+=rz-f; qE=0.0; CBE=0.0
        sell_E=False
        while sdi<len(sd) and sd[sdi][0]<=d:
            dist+=sum(s for dd,s in lots if dd<sd[sdi][0])*sd[sdi][1]*(1-wht); sdi+=1
        if armed:
            if G>0:
                pool=10000+b['시즌실현수익']; W=min(G,max(k,0.0)); px=sg[d]
                cb=W*fee/(1+fee); sh=(W-cb)/px; lots.append((d,sh)); cost_sep+=cb
                mb_new=T/pool; tgt=mb_new*b['현재보유개수']; e=max(0.0,qT-tgt)
                if e>1e-9:
                    c_=CBT*(e/qT); qT-=e; CBT-=c_; qE+=e; CBE+=c_
                seps.append(dict(detect=a['d'],exec=d,G=G,withdrawn=W,cash_before=k,full=(W>=G-1e-9),mb_before=mb,mb_after=mb_new,
                    new_excess_shares=e,new_excess_value=e*P,excess_total_shares=qE,excess_total_value=qE*P,sgov_px=px,shares=sh,cost=cb))
                k-=W; G-=W; mb=mb_new
            armed=False
        if excess_rule=='flat' and b['현재보유개수']==0 and qE>0: sell_E=True
        if X is not None and not armed and G>=T*X/100.0: armed=True
        if lots and d not in sg: raise SystemExit('SGOV 종가 없음 '+d)
        vault=sum(s for _,s in lots)*sg.get(d,0.0)+dist; op=k+(qT+qE)*P
        series.append((d,P,op,vault,op+vault,mb,qT,qE,k))
    return dict(series=series,seps=seps,exs=exs,cost_tab=cost_tab,cost_sep=cost_sep,cost_ex=cost_ex,dist=dist,short=short,capped=capped,yr=yr,G=G,
                min_cash=min(x[8] for x in series),qE_end=qE,qE_end_value=qE*rows[-1]['종가'],max_excess_value=max(x[7]*x[1] for x in series))
def stats(series):
    tot=[x[4] for x in series]; ds=[x[0] for x in series]
    D=lambda i,j:(dt.date.fromisoformat(ds[j])-dt.date.fromisoformat(ds[i])).days
    pk=0;mdd=0;mp=mt=0
    for i,v in enumerate(tot):
        if v>tot[pk]: pk=i
        if v/tot[pk]-1<mdd: mdd=v/tot[pk]-1;mp=pk;mt=i
    rec=next((i for i in range(mt,len(tot)) if tot[i]>=tot[mp]),None)
    eps=[];p=0;t=0
    for i in range(1,len(tot)):
        if tot[i]>=tot[p]:
            if tot[t]/tot[p]-1<=-0.10: eps.append(dict(peak=ds[p],trough=ds[t],dd=tot[t]/tot[p]-1,recovered=ds[i],days=D(p,i)))
            p=t=i
        elif tot[i]<tot[t]: t=i
    if tot[t]/tot[p]-1<=-0.10: eps.append(dict(peak=ds[p],trough=ds[t],dd=tot[t]/tot[p]-1,recovered=None,days=D(p,len(tot)-1)))
    return dict(start=ds[0],end=ds[-1],initial=tot[0],final=tot[-1],ret=tot[-1]/tot[0]-1,mdd=mdd,mdd_peak=ds[mp],mdd_trough=ds[mt],
        recovered=(ds[rec] if rec is not None else None),recovery_days=(D(mp,rec) if rec is not None else None),
        underwater_days=(None if rec is not None else D(mp,len(tot)-1)),episodes=eps)
SEGS=[('상승','2025-05-13','2026-06-22'),('급락','2026-06-22','2026-11-05'),('반등(진행중)','2026-11-05','2026-11-13'),
      ('세부급락','2025-10-29','2025-11-20'),('세부급락','2026-02-25','2026-03-30'),('세부급락','2026-06-22','2026-07-29'),('세부급락','2026-10-05','2026-11-05'),
      ('세부상승','2025-11-20','2026-02-25'),('세부상승','2026-03-30','2026-06-03')]
STRAT=[('B_compound',dict(X=None,reset='compound')),('B_fixed',dict(X=None,reset='fixed')),
       ('S30_compound',dict(X=30,reset='compound')),('S30_fixed',dict(X=30,reset='fixed'))]
SCEN={'C0':dict(fee=0.0,sec=0.0),'C1':dict(fee=0.0007,sec=0.0000206),'C2':dict(fee=0.0025,sec=0.0000206)}
SCEN_LABEL={'C0':'무비용','C1':'수수료 0.07% + SEC Fee 0.00206%(매도) — 확정 요율(주)','C2':'수수료 0.25% + SEC Fee 0.00206%(매도) — 참고'}
def main():
    v9p,sgp,sdp,out=sys.argv[1:5]; os.makedirs(out,exist_ok=True)
    rows,sg,sd=load(v9p,sgp,sdp); res={}
    for rule in('flat','reset','hold'):
        for sn,sp in SCEN.items():
            for name,kw in STRAT:
                if rule!='flat' and kw['X'] is None: continue
                r=run(rows,sg,sd,**kw,**sp,excess_rule=rule); st=stats(r['series']); m={x[0]:x[4] for x in r['series']}
                st.update(n_sep=len(r['seps']),seps=r['seps'],excess_sales=r['exs'],cost_table=r['cost_tab'],cost_sep=r['cost_sep'],cost_excess=r['cost_ex'],
                    cost_total=r['cost_tab']+r['cost_sep']+r['cost_ex'],op_final=r['series'][-1][2],vault_final=r['series'][-1][3],dist_net=r['dist'],
                    short_buys=r['short'],capped_sells=r['capped'],realized_net_by_year=r['yr'],G_end=r['G'],min_cash=r['min_cash'],
                    excess_end_shares=r['qE_end'],excess_end_value=r['qE_end_value'],max_excess_value=r['max_excess_value'],
                    seg={f'{k} {a}~{b}':m[b]/m[a]-1 for k,a,b in SEGS})
                res[f'{rule}|{sn}|{name}']=st
                if rule=='flat':
                    with open(os.path.join(out,f'series_{sn}_{name}.csv'),'w',newline='') as f:
                        w=csv.writer(f); w.writerow(['date','soxl_close','operating','sgov_vault','total','buy_multiplier','table_shares','excess_shares','cash'])
                        for x in r['series']: w.writerow([x[0],x[1]]+[round(v,4) for v in x[2:]])
    json.dump(res,open(os.path.join(out,'results_v3.json'),'w'),ensure_ascii=False,indent=1)
    pc=lambda v:f'{v*100:+.2f}%'; L=[]
    for rule,label in(('flat','본 계산 — 초과 보유: 표 보유 0 확인 다음 표일 종가에 전량 별도 매도'),('reset','민감도 — 초과 보유: 시즌 리셋 때 전량 매도'),('hold','민감도 — 초과 보유: 팔지 않고 끝까지 보유')):
        for sn in SCEN:
            L.append(f'== [{label}] {sn} ({SCEN_LABEL[sn]}) ==')
            L.append('전략 | 총수익률 | 최종(T=10000) | MDD | 고점→저점 | 회복 | 분리 | SGOV쪽 | 비용(표거래/분리/초과매도) | 매수부족일 | 매도축소일 | 끝 초과보유(주/평가) | 초과보유 최대평가')
            for name,_ in STRAT:
                s=res.get(f'{rule}|{sn}|{name}')
                if not s: continue
                rec=f"{s['recovered']} ({s['recovery_days']}일)" if s['recovered'] else f"미회복({s['underwater_days']}일째)"
                L.append(f"{name} | {pc(s['ret'])} | {s['final']:.0f} | {pc(s['mdd'])} | {s['mdd_peak']}→{s['mdd_trough']} | {rec} | {s['n_sep']} | {s['vault_final']:.0f} | {s['cost_total']:.0f} ({s['cost_table']:.0f}/{s['cost_sep']:.0f}/{s['cost_excess']:.0f}) | {len(s['short_buys'])} | {len(s['capped_sells'])} | {s['excess_end_shares']:.2f}/{s['excess_end_value']:.0f} | {s['max_excess_value']:.0f}")
            L.append('구간별 총자산 수익률')
            for k,a,b in SEGS: L.append(f'  {k} {a}~{b} | '+' | '.join(f"{n} {pc(res[f'{rule}|{sn}|{n}']['seg'][f'{k} {a}~{b}'])}" for n,_ in STRAT if f'{rule}|{sn}|{n}' in res))
            for name,_ in STRAT:
                s=res.get(f'{rule}|{sn}|{name}')
                if not s: continue
                L.append(f"{name}: 연도별 실현 순손익 "+', '.join(f'{y} {v:.0f}' for y,v in sorted(s['realized_net_by_year'].items()))+f" / SGOV 분배금(15% 원천징수 후) {s['dist_net']:.1f}")
                for e in s['episodes']: L.append(f"   낙폭 {e['peak']}→{e['trough']} {pc(e['dd'])} "+(f"회복 {e['recovered']} ({e['days']}일)" if e['recovered'] else f"미회복 ({e['days']}일째)"))
                for x in s['seps']: L.append(f"   분리 감지 {x['detect']} 실행 {x['exec']} 인출 {x['withdrawn']:.0f} (전액={x['full']}, 인출 전 현금 {x['cash_before']:.0f}) 매수배수 {x['mb_before']:.4f}→{x['mb_after']:.4f} 새 초과보유 {x['new_excess_shares']:.2f}주({x['new_excess_value']:.0f}) SGOV {x['sgov_px']}×{x['shares']:.3f}주 비용 {x['cost']:.1f}")
                for x in s['excess_sales']: L.append(f"   초과보유 매도 {x['date']} {x['shares']:.2f}주 × {x['price']} = {x['proceeds']:.0f} 실현 {x['realized']:+.1f} 비용 {x['cost']:.1f}")
                for x in s['short_buys']: L.append(f"   매수부족 {x[0]} 부족 {x[1]:.2f}주 / 목표 {x[2]:.2f}주")
                for x in s['capped_sells']: L.append(f"   매도축소 {x[0]} 축소 {x[1]:.2f}주 / 표×배수 {x[2]:.2f}주")
            L.append('')
    open(os.path.join(out,'summary_v3.txt'),'w').write('\n'.join(L)); print('\n'.join(L))
if __name__=='__main__': main()
