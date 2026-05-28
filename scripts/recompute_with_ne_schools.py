#!/usr/bin/env python3
import os, csv, json
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform
from pyproj import Transformer

# paths
ne_csv = None
for root,dirs,files in os.walk('data'):
    for f in files:
        if f.lower().startswith('north_east_schools') and f.lower().endswith('.csv'):
            ne_csv = os.path.join(root,f);
            break
    if ne_csv: break
if not ne_csv:
    print('North_East_schools.csv not found under data/')
    raise SystemExit(1)
print('Found NE schools CSV:', ne_csv)

ne_geo = 'data/NE_schools.geojson'
features = []
# try reading with utf-8, fallback to latin-1
open_kwargs = [{'encoding':'utf-8','errors':'strict'},{'encoding':'latin-1','errors':'replace'}]
for okw in open_kwargs:
    try:
        with open(ne_csv, newline='', **okw) as f:
            reader = csv.DictReader(f)
            hdrs = [h.lower() for h in reader.fieldnames]
            lat_keys = [k for k in reader.fieldnames if k.lower() in ('latitude','lat','y','latitudes','gps_lat')]
            lon_keys = [k for k in reader.fieldnames if k.lower() in ('longitude','lon','lng','x','long')]
            if not lat_keys or not lon_keys:
                for h in reader.fieldnames:
                    hl = h.lower()
                    if 'lat' in hl and not lat_keys:
                        lat_keys.append(h)
                    if ('lon' in hl or 'lng' in hl or 'long' in hl) and not lon_keys:
                        lon_keys.append(h)
            lat_col = lat_keys[0] if lat_keys else None
            lon_col = lon_keys[0] if lon_keys else None
            name_col = None
            for h in reader.fieldnames:
                if any(x in h.lower() for x in ('name','school','site','facility')):
                    name_col = h; break
            for row in reader:
                try:
                    lat = float(row[lat_col]) if lat_col and row.get(lat_col) else None
                    lon = float(row[lon_col]) if lon_col and row.get(lon_col) else None
                except:
                    lat = lon = None
                if lat is None or lon is None:
                    continue
                props = {}
                if name_col:
                    props['name'] = row.get(name_col,'')
                props['source']='North_East_schools.csv'
                features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[lon,lat]},'properties':props})
        break
    except Exception as e:
        print('Read attempt failed with', okw, 'error:', e)
        continue

with open(ne_geo,'w',encoding='utf-8') as fo:
    json.dump({'type':'FeatureCollection','features':features}, fo)
print('WROTE', ne_geo, len(features))

# Load LGAs
lga_file = 'data/lga_boundaries.geojson'
if not os.path.exists(lga_file):
    print('Missing LGA boundaries:', lga_file)
    raise SystemExit(1)
lgas = json.load(open(lga_file))
# Build LGA list with shapes
lga_list = []
for feat in lgas.get('features',[]):
    geom = shape(feat['geometry'])
    props = feat.get('properties',{})
    name = props.get('admin2') or props.get('NAME_2') or props.get('VARNAME_2') or props.get('name') or props.get('NAME_2')
    admin1 = props.get('admin1') or props.get('NAME_1') or props.get('NAME_1') or props.get('ADMIN')
    lga_list.append({'name': name, 'admin1': admin1, 'geom': geom, 'props': props})

# load idp points
idp_file = 'data/idp.geojson'
idp_points = []
if os.path.exists(idp_file):
    idpj = json.load(open(idp_file))
    for f in idpj.get('features',[]):
        coords = f['geometry']['coordinates']
        pt = Point(coords)
        pop = f.get('properties',{}).get('population')
        try: popv = float(pop) if pop not in (None,'') else 0.0
        except: popv = 0.0
        idp_points.append({'pt':pt,'pop':popv})

# load conflict points
conf_file = 'data/conflict.geojson'
conf_points = []
if os.path.exists(conf_file):
    cjson = json.load(open(conf_file))
    for f in cjson.get('features',[]):
        coords = f['geometry']['coordinates']
        pt = Point(coords)
        year = f.get('properties',{}).get('year')
        try: year = int(year)
        except: year = None
        conf_points.append({'pt':pt,'year':year})

# load new schools
schools_j = json.load(open(ne_geo))
school_points = []
for f in schools_j.get('features',[]):
    coords = f['geometry']['coordinates']
    pt = Point(coords)
    school_points.append({'pt':pt,'props':f.get('properties',{})})

# transformer to meters
transformer = Transformer.from_crs('epsg:4326','epsg:3857',always_xy=True)

# prepare per-LGA accumulators
for l in lga_list:
    l['schools'] = 0
    l['idp'] = 0.0
    l['conflict'] = 0
    l['conflict_deaths'] = 0.0

# count schools per LGA
for s in school_points:
    for l in lga_list:
        if l['geom'].contains(s['pt']):
            l['schools'] += 1
            break

# sum idp pop per LGA
for p in idp_points:
    for l in lga_list:
        if l['geom'].contains(p['pt']):
            l['idp'] += p['pop']
            break

# count conflicts
for c in conf_points:
    for l in lga_list:
        if l['geom'].contains(c['pt']):
            l['conflict'] += 1
            break

# load state-level pop and distribute
state_pop = {}
pop_csv = 'data/clean/bay_school_age_population_approx_2020.csv'
if os.path.exists(pop_csv):
    with open(pop_csv,newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            st = row['state']
            try: pop = float(row['population_5_17_approx'])
            except: pop = 0.0
            state_pop[st] = pop

# compute area in meters
for l in lga_list:
    geom_m = transform(lambda x,y: transformer.transform(x,y), l['geom'])
    l['area_m2'] = geom_m.area

# compute area totals per state
state_area = {}
for l in lga_list:
    st = l['admin1'] or ''
    state_area.setdefault(st,0.0)
    state_area[st] += l['area_m2']

# assign population per LGA
for l in lga_list:
    st = l['admin1'] or ''
    st_pop = state_pop.get(st)
    if st_pop is None:
        l['population'] = 0.0
    else:
        total_area = state_area.get(st,1.0)
        l['population'] = st_pop * (l['area_m2']/total_area if total_area>0 else 0.0)

# compute avg distance to nearest school for each LGA
school_coords_m = []
for s in school_points:
    x,y = transformer.transform(s['pt'].x, s['pt'].y)
    school_coords_m.append((x,y))

from math import inf
for l in lga_list:
    centroid = transform(lambda x,y: transformer.transform(x,y), l['geom']).centroid
    cx,cy = centroid.x, centroid.y
    min_d = inf
    for (sx,sy) in school_coords_m:
        dx = sx-cx; dy = sy-cy
        d = (dx*dx+dy*dy)**0.5
        if d<min_d: min_d = d
    l['avg_distance_m'] = min_d if min_d<inf else 0.0
    l['pop_per_school'] = l['population']/(l['schools']+1)

# normalize and compute gap_index
vals_pop = [l['pop_per_school'] for l in lga_list]
vals_dist = [l['avg_distance_m'] for l in lga_list]
vals_conf = [l['conflict'] for l in lga_list]
vals_idp = [l['idp'] for l in lga_list]

def normalize(arr):
    mn = min(arr); mx = max(arr)
    if mx==mn:
        return [0.0 for _ in arr]
    return [(v-mn)/(mx-mn) for v in arr]

n_pop = normalize(vals_pop)
n_dist = normalize(vals_dist)
n_conf = normalize(vals_conf)
n_idp = normalize(vals_idp)
for i,l in enumerate(lga_list):
    l['norm_pop']=n_pop[i]
    l['norm_dist']=n_dist[i]
    l['norm_conflict']=n_conf[i]
    l['norm_idp']=n_idp[i]
    l['gap_index']=0.35*l['norm_pop'] + 0.25*l['norm_dist'] + 0.25*l['norm_conflict'] + 0.15*l['norm_idp']

# write processed geojson and csv
os.makedirs('data/processed', exist_ok=True)
feats=[]
for l in lga_list:
    feat={'type':'Feature','geometry':mapping(l['geom']),'properties':{
        'LGA_name': l['name'],'admin1':l['admin1'],'schools':l['schools'],'population':l['population'],'idp':l['idp'],'conflict':l['conflict'],'pop_per_school':l['pop_per_school'],'avg_distance_m':l['avg_distance_m'],'gap_index':l['gap_index']
    }}
    feats.append(feat)
open('data/processed/lga_gap_index.geojson','w',encoding='utf-8').write(json.dumps({'type':'FeatureCollection','features':feats}))
# csv
with open('data/processed/lga_gap_index.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['LGA_name','admin1','schools','population','idp','conflict','pop_per_school','avg_distance_m','gap_index'])
    for l in lga_list:
        w.writerow([l['name'],l['admin1'],l['schools'],l['population'],l['idp'],l['conflict'],l['pop_per_school'],l['avg_distance_m'],l['gap_index']])
print('WROTE updated lga_gap_index.geojson and csv')
