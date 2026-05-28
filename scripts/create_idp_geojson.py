#!/usr/bin/env python3
import csv, json, glob, os
files=glob.glob('data/clean/bay_idp_sites_clean_*.csv')
out=os.path.join('data','idp.geojson')
features=[]
if files:
    fpath=sorted(files)[-1]
    with open(fpath,newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            lat=r.get('latitude',''); lon=r.get('longitude','')
            try:
                latf=float(lat); lonf=float(lon)
            except:
                continue
            pop=r.get('population','')
            try:
                popv=float(pop)
            except:
                popv=None
            props={'site_name': r.get('site_name',''), 'site_type': r.get('site_type',''), 'population': popv, 'state': r.get('state','')}
            features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[lonf,latf]},'properties':props})
    with open(out,'w',encoding='utf-8') as fo:
        json.dump({'type':'FeatureCollection','features':features}, fo, ensure_ascii=False)
    print('WROTE', out, len(features))
else:
    print('No idp clean file found')
