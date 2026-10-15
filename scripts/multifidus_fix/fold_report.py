# 候補 npz の各パーツについて、折れ辺（隣り合う面の向きが 120° 以上違う辺）を男性・今・候補で数え、辺の長さの比（今→候補）を出す（システムの Python）
# python fold_report.py <work/g4> <候補 npz>
import sys, json, numpy as np
W, CAND = sys.argv[1:3]
fj=json.load(open(W+"/female.json",encoding="utf-8")); F=np.load(W+"/female.npz")
mj=json.load(open(W+"/male.json",encoding="utf-8")); M=np.load(W+"/male.npz"); N=np.load(CAND)
def tris(D, s):
    lv,ls,lt=D["fl_%d"%s],D["fs_%d"%s],D["ft_%d"%s]; out=[]
    for k in range(3,int(lt.max())+1):
        sel=np.where(lt==k)[0]
        for j in range(1,k-1): out.append(np.stack([lv[ls[sel]],lv[ls[sel]+j],lv[ls[sel]+j+1]],1))
    return np.concatenate(out)
def adj(T):
    e = np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]); f = np.tile(np.arange(len(T)),3)
    e.sort(1); key = e[:,0].astype(np.int64)*10**7+e[:,1]; o = np.argsort(key,kind="stable"); key=key[o]; f=f[o]
    same = key[1:]==key[:-1]; return f[:-1][same], f[1:][same]
def folds(W_, T, A):
    n = np.cross(W_[T[:,1]]-W_[T[:,0]], W_[T[:,2]]-W_[T[:,0]]); n /= np.maximum(np.linalg.norm(n,axis=1),1e-30)[:,None]
    d = (n[A[0]]*n[A[1]]).sum(1); return int((d < -0.5).sum())
rows=[]
for k in N.files:
    s=fj["full"][k]; T=tris(F,s); A=adj(T); a=F["w_%d"%s].astype(float); b=N[k].astype(float); E=F["e_%d"%s]
    fm="-"; ref=a
    if k in mj["full"] and mj["meta"][k]["n"]==fj["meta"][k]["n"] and mj["meta"][k]["sig"]==fj["meta"][k]["sig"]:
        sm=mj["full"][k]; Tm=tris(M,sm); X=M["w_%d"%sm].astype(float); fm=folds(X,Tm,adj(Tm))
        if any(t in k for t in ("腹横筋","内腹斜筋","腹直筋","錐体筋")): ref=X        # 作り直したパーツは男性の形と比べる
    la=np.linalg.norm(ref[E[:,0]]-ref[E[:,1]],axis=1); lb=np.linalg.norm(b[E[:,0]]-b[E[:,1]],axis=1); r=lb[la>1e-9]/la[la>1e-9]
    if ref is not a: r = r / np.median(r)                                           # 男性との比は全体の倍率で割る
    rows.append((k,fm,folds(a,T,A),folds(b,T,A),round(float(np.percentile(r,0.1)),2),round(float(np.percentile(r,99.9)),2), "男" if ref is not a else "今"))
print("パーツ  折れ辺 男性 / 今 / 候補   辺の長さの比（基準→候補, 0.1%点〜99.9%点） 基準")
for r in sorted(rows,key=lambda r:-(r[3]-r[2])):
    if r[2]!=r[3] or r[4]<0.8 or r[5]>1.25: print("  %-12s %4s / %4d / %4d   %.2f〜%.2f  %s"%r)
print("（折れの数が同じで、辺の比が 0.8〜1.25 に収まるパーツは省略）")
