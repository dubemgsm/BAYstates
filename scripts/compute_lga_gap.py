#!/usr/bin/env python3
import json, os
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform
from pyproj import Transformer

# paths
lga_file='data/lga_boundaries.geojson'
schools_file='data/schools.geojson'
idp_file='data/idp.geojson'
pop_state_csv='data/clean/bay_school_age_population_approx_2020.csv'
out_geo='data/processed/lga_gap_index.geojson'
out_csv='data/processed/lga_gap_index.csv'

os.makedirs('data/processed', exist_ok=True)
# load LGAs
with open(lga_file) as f:
    lga_col=json.load(f)
lgas = []
for feat in lga_col.get('features',[]):
    geom = shape(feat['geometry'])
    props = feat.get('properties',{})
    name = props.get('name') or props.get('ADMIN') or props.get('admin1')
    lgas.append({'name':name,'geom':geom,'props':props})
# project to equal-area for area calc and distance
transformer = Transformer.from_crs('epsg:4326','epsg:3857',always_xy=True)
for l in lgas:
    l['geom_m'] = transform(lambda x,y: transformer.transform(x,y), l['geom'])
    l['area'] = l['geom_m'].area
# load schools
with open(schools_file) as f:
    schools=json.load(f)
school_points=[]
for feat in schools.get('features',[]):
    pt = Point(feat['geometry']['coordinates'])
    school_points.append({'pt':pt,'props':feat.get('properties',{})})
# load idps
with open(idp_file) as f:
    idps=json.load(f)
idp_points=[]
for feat in idps.get('features',[]):
    coords=feat['geometry']['coordinates']
    pt=Point(coords)
    pop = feat.get('properties',{}).get('population')
    try:
        popv=float(pop) if pop not in (None,'') else 0.0
    except:
        popv=0.0
    idp_points.append({'pt':pt,'pop':popv,'props':feat.get('properties',{})})
# compute schools per LGA and idp pop per LGA
for l in lgas:
    l['schools']=0
    l['idp_pop']=0.0
for s in school_points:
    for l in lgas:
        if l['geom'].contains(s['pt']):
            l['schools'] += 1
            break
for p in idp_points:
    for l in lgas:
        if l['geom'].contains(p['pt']):
            l['idp_pop'] += p['pop']
            break
# load state pop and distribute to LGAs by area proportion
state_pop = {}
import csv
if os.path.exists(pop_state_csv):
    with open(pop_state_csv,newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            state = row['state']
            try:
                pop = float(row['population_5_17_approx'])
            except:
                pop = 0.0
            state_pop[state]=pop
# compute total area per state
state_area = {}
for l in lgas:
    st = l['props'].get('name')
    # GADM NAME_1 is probably in properties? We used admin1 earlier
    # For each lga, props have 'admin1' maybe; try to extract admin1 from properties
    admin1 = l['props'].get('admin1') or l['props'].get('NAME_1') or l['props'].get('admin1_name') or l['props'].get('ADMIN')
    if admin1 is None:
        admin1 = ''
    l['admin1']=admin1
    state_area.setdefault(admin1,0.0)
    state_area[admin1] += l['area']
# assign population per LGA proportional to area within its state
for l in lgas:
    admin1 = l['admin1']
    state_total = state_pop.get(admin1, None)
    if state_total is None:
        l['population']=0.0
    else:
        total_area = state_area.get(admin1,1.0)
        l['population'] = state_total * (l['area']/total_area if total_area>0 else 0.0)
# compute indicators
import math
for l in lgas:
    l['pop_per_school'] = l['population'] / (l['schools'] + 1)
    # approximate avg distance: compute centroid to nearest school distance in meters
    if school_points:
        centroid = l['geom_m'].centroid
        # find nearest school in meters by projecting school point
        min_d = float('inf')
        for s in school_points:
            sx,sy = transformer.transform(s['pt'].x, s['pt'].y)
            d = centroid.distance(Point(sx,sy))
            if d < min_d:
                min_d = d
        l['avg_distance'] = min_d
    else:
        l['avg_distance'] = 0.0
    l['conflict'] = 0.0
    l['idp'] = l['idp_pop']
# normalize
vals_pop = [l['pop_per_school'] for l in lgas]
vals_dist = [l['avg_distance'] for l in lgas]
vals_conf = [l['conflict'] for l in lgas]
vals_idp = [l['idp'] for l in lgas]

def normalize(arr):
    mn = min(arr); mx = max(arr)
    if mx==mn:
        return [0.0 for _ in arr]
    return [(v-mn)/(mx-mn) for v in arr]
norm_pop = normalize(vals_pop)
norm_dist = normalize(vals_dist)
norm_conf = normalize(vals_conf)
norm_idp = normalize(vals_idp)
for i,l in enumerate(lgas):
    l['norm_pop']=norm_pop[i]
    l['norm_dist']=norm_dist[i]
    l['norm_conflict']=norm_conf[i]
    l['norm_idp']=norm_idp[i]
    # weighted gap index
    l['gap_index'] = 0.35*l['norm_pop'] + 0.25*l['norm_dist'] + 0.25*l['norm_conflict'] + 0.15*l['norm_idp']
# write geojson and csv
feats=[]
for l in lgas:
    feat={'type':'Feature','geometry':mapping(l['geom']),'properties':{
        'LGA_name': l['name'],'admin1':l['admin1'],'schools':l['schools'],'population':l['population'],'idp':l['idp'],'pop_per_school':l['pop_per_school'],'avg_distance_m':l['avg_distance'],'gap_index':l['gap_index']
    }}
    feats.append(feat)
geo={'type':'FeatureCollection','features':feats}
open(out_geo,'w',encoding='utf-8').write(json.dumps(geo))
# csv
import csv
with open(out_csv,'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['LGA_name','admin1','schools','population','idp','pop_per_school','avg_distance_m','gap_index'])
    for l in lgas:
        w.writerow([l['name'],l['admin1'],l['schools'],l['population'],l['idp'],l['pop_per_school'],l['avg_distance'],l['gap_index']])
print('WROTE', out_geo, out_csv)
