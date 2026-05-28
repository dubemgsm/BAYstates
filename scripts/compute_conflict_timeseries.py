#!/usr/bin/env python3
import csv, os
from collections import defaultdict
infile = os.path.join('data','clean','conflict_data_bay.csv')
out_year = os.path.join('data','processed','conflict_timeseries_yearly.csv')
out_state = os.path.join('data','processed','conflict_timeseries_state_yearly.csv')
out_lga = os.path.join('data','processed','conflict_timeseries_lga_yearly.csv')
if not os.path.exists(infile):
    print('Input missing', infile)
    raise SystemExit(1)

year_counts = defaultdict(int)
year_deaths = defaultdict(float)
state_year_counts = defaultdict(int)
state_year_deaths = defaultdict(float)
lga_year_counts = defaultdict(int)
lga_year_deaths = defaultdict(float)

with open(infile, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        year_raw = row.get('year','').strip()
        try:
            year = int(year_raw)
        except:
            continue
        deaths = 0.0
        try:
            deaths = float(row.get('deaths') or 0)
        except:
            deaths = 0.0
        state = row.get('adm_1') or row.get('country') or ''
        lga = row.get('adm_2') or ''
        year_counts[year] += 1
        year_deaths[year] += deaths
        state_year_counts[(state,year)] += 1
        state_year_deaths[(state,year)] += deaths
        lga_year_counts[(state,lga,year)] += 1
        lga_year_deaths[(state,lga,year)] += deaths

# write overall yearly
with open(out_year,'w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['year','count','deaths'])
    for y in sorted(year_counts):
        w.writerow([y, year_counts[y], int(year_deaths[y]) if year_deaths[y].is_integer() else round(year_deaths[y],2)])

# write state-year
with open(out_state,'w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['state','year','count','deaths'])
    keys = sorted(state_year_counts.keys(), key=lambda x:(x[0] or '', x[1]))
    for (state,y) in keys:
        w.writerow([state,y,state_year_counts[(state,y)], int(state_year_deaths[(state,y)]) if state_year_deaths[(state,y)].is_integer() else round(state_year_deaths[(state,y)],2)])

# write lga-year
with open(out_lga,'w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['state','lga','year','count','deaths'])
    keys = sorted(lga_year_counts.keys(), key=lambda x:(x[0] or '', x[1] or '', x[2]))
    for (state,lga,y) in keys:
        w.writerow([state,lga,y,lga_year_counts[(state,lga,y)], int(lga_year_deaths[(state,lga,y)]) if lga_year_deaths[(state,lga,y)].is_integer() else round(lga_year_deaths[(state,lga,y)],2)])

# print quick summary
all_years = sorted(year_counts)
if all_years:
    latest = all_years[-1]
    print('Years covered:', all_years[0], '-', latest)
    print('Total events:', sum(year_counts.values()))
    print('Events in latest year', latest, year_counts[latest])
else:
    print('No events')
