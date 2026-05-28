#!/usr/bin/env python3
import json, os
infile=None
lst=[p for p in os.listdir(os.path.join('data','raw')) if p.startswith('bay_lga_overpass_') and p.endswith('.json')]
if lst:
    infile=os.path.join('data','raw',sorted(lst)[-1])
out='data/lga_boundaries.geojson'
if infile:
    j=json.load(open(infile))
    feats=[]
    for el in j.get('elements',[]):
        if el.get('type') in ('relation','way'):
            geom=el.get('geometry')
            if not geom:
                continue
            coords=[[p['lon'],p['lat']] for p in geom]
            if len(coords)>=4 and coords[0]==coords[-1]:
                g={'type':'Polygon','coordinates':[coords]}
            else:
                # fallback to LineString
                g={'type':'LineString','coordinates':coords}
            props={'name': el.get('tags',{}).get('name',''), 'osm_id': el.get('id')}
            feats.append({'type':'Feature','geometry':g,'properties':props})
    with open(out,'w',encoding='utf-8') as f:
        json.dump({'type':'FeatureCollection','features':feats}, f, ensure_ascii=False)
    print('WROTE', out, len(feats))
else:
    print('No overpass file to convert')
