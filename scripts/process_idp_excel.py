#!/usr/bin/env python3
import sys, os, re
import pandas as pd

infile = sys.argv[1]
rawdir = sys.argv[2]
cleandir = sys.argv[3]
ts = sys.argv[4]

xls = pd.read_excel(infile, sheet_name=None, engine='openpyxl')
out_rows = []
for sheetname, df in xls.items():
    safe = re.sub(r'[^0-9A-Za-z_]+', '_', sheetname)[:50]
    csvpath = os.path.join(rawdir, f"{ts}_{safe}.csv")
    df.to_csv(csvpath, index=False, encoding='utf-8')
    print(f"WROTE {csvpath}")
    # lower-case col map
    cols = {c.lower().strip(): c for c in df.columns}
    state_col = None
    for k in cols:
        if any(x in k for x in ('state','admin1','adm1','province','region','gov')):
            state_col = cols[k]
            break
    lat_col = None; lon_col = None
    for k in cols:
        if k in ('latitude','lat','y'):
            lat_col = cols[k]
        if k in ('longitude','lon','x'):
            lon_col = cols[k]
    name_col = None
    for k in cols:
        if any(x in k for x in ('site','location','name','camp','settlement')):
            name_col = cols[k]
            break
    pop_col = None
    for k in cols:
        if any(x in k for x in ('population','pop','total')):
            pop_col = cols[k]
            break
    type_col = None
    for k in cols:
        if 'type' in k or 'site_type' in k:
            type_col = cols[k]
            break
    if state_col:
        mask = df[state_col].astype(str).str.contains(r'Borno|Adamawa|Yobe', case=False, na=False)
    else:
        # fallback: search any cell
        mask = df.apply(lambda row: any(('borno' in str(v).lower() or 'adamawa' in str(v).lower() or 'yobe' in str(v).lower()) for v in row.values), axis=1)
    sel = df[mask]
    for _, row in sel.iterrows():
        name = row[name_col] if name_col in row and pd.notna(row[name_col]) else ''
        lat = row[lat_col] if lat_col and lat_col in row and pd.notna(row[lat_col]) else ''
        lon = row[lon_col] if lon_col and lon_col in row and pd.notna(row[lon_col]) else ''
        st = row[state_col] if state_col and state_col in row and pd.notna(row[state_col]) else ''
        pop = row[pop_col] if pop_col and pop_col in row and pd.notna(row[pop_col]) else ''
        typ = row[type_col] if type_col and type_col in row and pd.notna(row[type_col]) else ''
        out_rows.append({'site_name':str(name),'latitude':lat,'longitude':lon,'site_type':str(typ),'population':pop,'state':str(st),'source_sheet':sheetname})

if out_rows:
    outpath = os.path.join(cleandir, f'bay_idp_sites_clean_{ts}.csv')
    import csv
    keys = ['site_name','latitude','longitude','site_type','population','state','source_sheet']
    with open(outpath,'w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out_rows)
    print('WROTE', outpath)
else:
    print('No BAY records found')
