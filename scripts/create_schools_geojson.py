#!/usr/bin/env python3
import csv, json, os
infile=os.path.join('data','clean','bay_nigeria_schools_clean.csv')
out=os.path.join('data','schools.geojson')
features=[]
if os.path.exists(infile):
    with open(infile, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            lat=r.get('latitude','').strip(); lon=r.get('longitude','').strip()
            try:
                latf=float(lat); lonf=float(lon)
            except:
                continue
            props={'name': r.get('name',''), 'type': r.get('type',''), 'state': r.get('state','')}
            features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[lonf,latf]},'properties':props})
    with open(out,'w',encoding='utf-8') as f:
        json.dump({'type':'FeatureCollection','features':features}, f, ensure_ascii=False)
    print('WROTE', out, len(features))
else:
    print('Missing', infile)
