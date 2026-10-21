# build_dashboard.py
# Re-runs the evaluation and clustering behind the dashboard and writes dashboard/index.html
# Run from the repository root after the src/ pipeline:  python analysis/build_dashboard.py

import glob
import json
import os
import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import silhouette_score
from sklearn.model_selection import KFold, RepeatedKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

# Paths (outputs of the src/ pipeline)
DEMOGRAPHIC_PATH = 'data_org/Demographic.xlsx'
RAW_FOLDER = 'data_org/SCH_asthma_114'
BY_COMPLETENESS = 'data_read/patients_by_completeness'
YEARLY_FOLDER = 'data_read/cleaned_patients_by_yearly_data'
IMPUTED_FOLDER = 'data_read/imputed_data'
STATS_PATH = 'Consolidated_Patient_PEFR_Statistics.xlsx'
TEMPLATE = 'dashboard/template.html'
OUTPUT = 'dashboard/index.html'
LEVELS = ['high', 'medium', 'low']

out = {}

# ---------- patient funnel ----------
demo = pd.read_excel(DEMOGRAPHIC_PATH)
n_files = len([f for f in os.listdir(RAW_FOLDER) if f.endswith('.xlsx')])
n_matched = sum(len(os.listdir(f'{BY_COMPLETENESS}/{l}_completeness')) for l in LEVELS)
n_kept = sum(len(os.listdir(f'{IMPUTED_FOLDER}/{l}_completeness')) for l in LEVELS)
out['funnel'] = [
    {'step': 'Patients in demographic sheet', 'n': len(demo)},
    {'step': 'Patient PEFR files received', 'n': n_files},
    {'step': 'Files matched to a demographic ID', 'n': n_matched},
    {'step': 'Span ≥ 1 year of readings', 'n': n_kept},
]
out['tiers'] = {l: [len(os.listdir(f'{BY_COMPLETENESS}/{l}_completeness')),
                    len(os.listdir(f'{IMPUTED_FOLDER}/{l}_completeness'))] for l in LEVELS}

# ---------- completeness per PEFR column ----------
comp = {'am': [], 'pm': [], 'other': []}
for f in glob.glob(f'{BY_COMPLETENESS}/*/*.csv'):
    d = pd.read_csv(f)
    for k in comp:
        comp[k].append(d['pefr_' + k].notna().mean())
out['colcomp'] = {k: round(float(np.mean(v)), 3) for k, v in comp.items()}

# ---------- missing cells before / after imputation ----------
before = {'am': 0, 'pm': 0, 'other': 0}
after = {'am': 0, 'pm': 0, 'other': 0}
rows = 0
for l in LEVELS:
    for f in glob.glob(f'{YEARLY_FOLDER}/{l}_completeness/*.csv'):
        pid = os.path.basename(f)[:-4]
        a = pd.read_csv(f)
        b = pd.read_csv(f'{IMPUTED_FOLDER}/{l}_completeness/imputed_cleaned_{pid}.csv')
        rows += len(b)
        for k in before:
            before[k] += int(pd.to_numeric(a['pefr_' + k], errors='coerce').isna().sum())
            after[k] += int(pd.to_numeric(b['pefr_' + k], errors='coerce').isna().sum())
out['imputation'] = {'rows': rows, 'missing_before': before, 'missing_after': after}

# ---------- weekly AM / PM series per patient ----------
series = {}
for f in glob.glob(f'{IMPUTED_FOLDER}/*/*.csv'):
    pid = os.path.basename(f).replace('imputed_cleaned_', '')[:-4]
    d = pd.read_csv(f)
    d['date'] = pd.to_datetime(d['date'], errors='coerce')
    d = d.dropna(subset=['date'])
    for k in ['pefr_am', 'pefr_pm']:
        d[k] = pd.to_numeric(d[k], errors='coerce')
    w = d.set_index('date')[['pefr_am', 'pefr_pm']].resample('W').mean().dropna(how='all')
    series[pid] = {'d': [x.strftime('%Y-%m-%d') for x in w.index],
                   'am': [None if pd.isna(v) else round(v) for v in w['pefr_am']],
                   'pm': [None if pd.isna(v) else round(v) for v in w['pefr_pm']]}
out['series'] = series

# ---------- merged modeling table (AM statistics + demographics) ----------
stats = pd.read_excel(STATS_PATH)
stats = stats[['patient_id'] + [c for c in stats.columns if c.startswith('pefr_am_')]]
stats = stats.rename(columns=lambda c: c.replace('pefr_am_', 'pefr_'))
d = demo.rename(columns=str.lower)
m = d[['id', 'age', 'sex', 'smoke', 'smoke_amount', 'height', 'weight', 'bmi', 'bsa', 'address']] \
    .merge(stats, left_on='id', right_on='patient_id')
m = m.dropna(subset=['pefr_mean', 'pefr_std', 'pefr_skew'])   # drops patients with < 2 AM readings
m['region'] = m['address'].fillna('').str.split().str[0]
m.loc[~m['region'].isin(['Gyeonggi-do', 'Incheon', 'Seoul']), 'region'] = 'Other'
m['sex_f'] = (m['sex'] == 'F').astype(int)
m['smoke_code'] = m['smoke'].map({'SM': 0, 'ES': 1, 'NS': 2})
m['ever_smoker'] = (m['smoke'] != 'NS').astype(int)
for r in ['Incheon', 'Seoul', 'Other']:
    m['reg_' + r] = (m['region'] == r).astype(int)

# only non-identifying fields go into the public page
out['patients'] = m[['id', 'age', 'height', 'pefr_count', 'pefr_min', 'pefr_median', 'pefr_max',
                     'pefr_mean', 'pefr_std']].round(2).replace({np.nan: None}).to_dict('records')

# ---------- Spearman correlation with mean AM PEFR ----------
demo_cols = ['age', 'sex_f', 'ever_smoker', 'smoke_amount', 'height', 'weight', 'bmi', 'bsa']
out['corr_target'] = [{'f': c, 'r': round(m[c].corr(m['pefr_mean'], method='spearman'), 2)} for c in demo_cols]

# ---------- regression: PEFR-derived (leaky) features vs demographics only ----------
leaky = ['age', 'sex_f', 'smoke_code', 'smoke_amount', 'height', 'weight', 'bmi', 'bsa', 'pefr_count',
         'pefr_min', 'pefr_median', 'pefr_max', 'pefr_sum', 'pefr_std', 'pefr_skew']
demof = ['age', 'sex_f', 'ever_smoker', 'smoke_amount', 'height', 'weight', 'bmi', 'bsa',
         'reg_Incheon', 'reg_Seoul', 'reg_Other']
y = m['pefr_mean'].values
rkf = RepeatedKFold(n_splits=5, n_repeats=20, random_state=0)


def cv(model, X):
    r2 = cross_val_score(model, X, y, cv=rkf, scoring='r2')
    rmse = -cross_val_score(model, X, y, cv=rkf, scoring='neg_root_mean_squared_error')
    return {'r2': round(r2.mean(), 3), 'r2_sd': round(r2.std(), 3), 'rmse': round(rmse.mean(), 1)}


models = {
    'Linear': LinearRegression(),
    'Ridge': make_pipeline(StandardScaler(), Ridge(alpha=10)),
    'Lasso': make_pipeline(StandardScaler(), Lasso(alpha=1, max_iter=50000)),
    'Random forest': RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=0),
}
results = [{'model': 'Baseline (predict average)', 'set': '—', **cv(DummyRegressor(), m[demof])},
           {'model': 'pefr_median alone', 'set': 'leaky', **cv(LinearRegression(), m[['pefr_median']])}]
for name, model in models.items():
    results.append({'model': name, 'set': 'leaky', **cv(model, m[leaky])})
for name, model in models.items():
    results.append({'model': name, 'set': 'demographic', **cv(model, m[demof])})
out['models'] = results

kf = KFold(5, shuffle=True, random_state=42)
pred_leaky = cross_val_predict(LinearRegression(), m[leaky], y, cv=kf)
pred_demo = cross_val_predict(make_pipeline(StandardScaler(), Ridge(alpha=10)), m[demof], y, cv=kf)
out['pva'] = [{'id': i, 'actual': round(a, 1), 'leaky': round(b, 1), 'demo': round(c, 1)}
              for i, a, b, c in zip(m['id'], y, pred_leaky, pred_demo)]

rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=0).fit(m[demof], y)
ridge = make_pipeline(StandardScaler(), Ridge(alpha=10)).fit(m[demof], y)
out['importance'] = [{'f': f, 'rf': round(a, 3), 'ridge': round(b, 1)}
                     for f, a, b in zip(demof, rf.feature_importances_, ridge[-1].coef_)]

# ---------- k-means on strength and stability of AM PEFR ----------
m['pefr_cv'] = m['pefr_std'] / m['pefr_mean']
m['pefr_range_pct'] = (m['pefr_max'] - m['pefr_min']) / m['pefr_mean']
Xc = StandardScaler().fit_transform(m[['pefr_mean', 'pefr_cv', 'pefr_range_pct']])
out['silhouette'] = []
for k in range(2, 7):
    km = KMeans(k, n_init=50, random_state=0).fit(Xc)
    out['silhouette'].append({'k': k, 'sil': round(silhouette_score(Xc, km.labels_), 3)})

K = 4   # k = 4 and 5 are near-tied on silhouette; 4 is simpler
km = KMeans(K, n_init=50, random_state=0).fit(Xc)
order = m.groupby(km.labels_)['pefr_mean'].mean().sort_values().index.tolist()   # cluster 0 = lowest PEFR
m['cluster'] = [order.index(l) for l in km.labels_]
profile = m.groupby('cluster').agg(n=('id', 'count'), pefr_mean=('pefr_mean', 'mean'), pefr_cv=('pefr_cv', 'mean'),
                                   age=('age', 'mean'), height=('height', 'mean'), bmi=('bmi', 'mean'),
                                   female=('sex_f', 'mean'), ever_smoker=('ever_smoker', 'mean'))
out['clusters'] = profile.round(3).reset_index().to_dict('records')
out['cluster_pts'] = [{'id': i, 'c': int(c), 'mean': round(a, 1), 'cv': round(b, 3)}
                      for i, c, a, b in zip(m['id'], m['cluster'], m['pefr_mean'], m['pefr_cv'])]

# ---------- write the dashboard ----------
data = json.dumps(out, separators=(',', ':'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
with open(TEMPLATE) as f:
    html = f.read().replace('__DATA__', data)
with open(OUTPUT, 'w') as f:
    f.write(html)

print(f'Patients modeled: {len(m)}')
for r in results:
    print(f"  {r['model']:<28} {r['set']:<12} R² {r['r2']:>6.3f} ± {r['r2_sd']:.3f}")
print(f'Dashboard written to {OUTPUT}')
