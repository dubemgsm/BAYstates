#!/usr/bin/env python3
import json, csv, os
# paths
bounds_file = 'data/raw/bay_bounds.json'
pop_csv = 'data/clean/bay_school_age_population_approx_2020.csv'
states_geo = 'data/states.geojson'
schools_geo = 'data/schools.geojson'
idp_geo = 'data/idp.geojson'
map_html = 'visuals/education_barriers_ne_map.html'
# read bounds
with open(bounds_file) as f:
    bounds = json.load(f)
# read pop csv
pop_map = {}
if os.path.exists(pop_csv):
    with open(pop_csv, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = r['state']
            try:
                pop = float(r['population_5_17_approx'])
            except:
                pop = None
            pop_map[name] = pop
# create states GeoJSON (rectangles)
feats = []
for b in bounds:
    name = b.get('name')
    minlat = b.get('minlat'); minlon = b.get('minlon'); maxlat = b.get('maxlat'); maxlon = b.get('maxlon')
    coords = [[minlon,minlat],[maxlon,minlat],[maxlon,maxlat],[minlon,maxlat],[minlon,minlat]]
    props = {'name': name, 'population_5_17_approx': pop_map.get(name)}
    feats.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[coords]},'properties':props})
with open(states_geo,'w',encoding='utf-8') as f:
    json.dump({'type':'FeatureCollection','features':feats}, f, ensure_ascii=False)
print('WROTE', states_geo)
# prepare population JS mapping
pop_js = json.dumps({k: (v if v is not None else 0) for k,v in pop_map.items()})
# Write HTML map using placeholder for pop_js
html_template = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>BAY Education Barriers (NE Nigeria)</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.3/dist/leaflet.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<style> body{font-family:sans-serif;margin:0;padding:0} #map{position:absolute;top:40px;bottom:0;left:0;right:0} header{position:fixed;top:0;left:0;right:0;height:40px;background:#fff;z-index:1000;padding:8px;box-shadow:0 1px 2px rgba(0,0,0,0.1)} .legend{background:white;padding:6px;border-radius:4px;font-size:12px}</style>
</head>
<body>
<header><strong>BAY Education Barriers — Borno, Adamawa, Yobe</strong></header>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.3/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
var pop_map = __POP_JS__;
function getColor(d){
    return d>3000000 ? '#800026' : d>2000000 ? '#BD0026' : d>1000000 ? '#E31A1C' : d>500000 ? '#FC4E2A' : d>100000 ? '#FD8D3C' : '#FEB24C';
}
var map = L.map('map').setView([10.5,12.5],7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OSM'}).addTo(map);
// States layer
fetch('../data/states.geojson').then(r=>r.json()).then(function(data){
    function style(feat){
        var pop = pop_map[feat.properties.name] || 0;
        return {fillColor:getColor(pop), weight:2, opacity:1, color:'#444', fillOpacity:0.5}
    }
    L.geoJSON(data,{style:style,onEachFeature:function(f,l){l.bindPopup('<b>'+f.properties.name+'</b><br/>School-age pop (approx): '+(pop_map[f.properties.name]||0).toLocaleString())}}).addTo(map);
});
// Schools
fetch('../data/schools.geojson').then(r=>r.json()).then(function(data){
    var schools = L.layerGroup();
    data.features.forEach(function(f){
        var c = f.geometry.coordinates; var m = L.circleMarker([c[1],c[0]],{radius:4,fillColor:'green',color:'#0a0',weight:1,fillOpacity:0.9});
        m.bindPopup('<b>School</b><br/>'+(f.properties.name||'')+'<br/>'+(f.properties.type||''));
        schools.addLayer(m);
    });
    schools.addTo(map);
});
// IDP cluster
fetch('../data/idp.geojson').then(r=>r.json()).then(function(data){
    var markers = L.markerClusterGroup();
    data.features.forEach(function(f){
        var c = f.geometry.coordinates; var props = f.properties||{};
        var m = L.marker([c[1],c[0]]);
        var popup = '<b>IDP site</b><br/>' + (props.site_name||'') + '<br/>State: '+(props.state||'') + '<br/>Pop: '+(props.population||'');
        m.bindPopup(popup);
        markers.addLayer(m);
    });
    map.addLayer(markers);
});
// Legend
var legend = L.control({position:'bottomright'});
legend.onAdd = function(map){
    var div = L.DomUtil.create('div','legend');
    var grades = [0,100000,500000,1000000,2000000,3000000];
    div.innerHTML = '<b>School-age pop (approx)</b><br/>';
    for(var i=0;i<grades.length;i++){
        div.innerHTML += '<i style="background:'+getColor(grades[i]+1)+';width:18px;height:12px;display:inline-block;margin-right:6px"></i> ' + grades[i].toLocaleString() + (grades[i+1]? '&ndash;'+grades[i+1].toLocaleString() : '+') + '<br/>';
    }
    return div;
};
legend.addTo(map);
</script>
</body>
</html>
'''
html = html_template.replace('__POP_JS__', pop_js)
with open(map_html,'w',encoding='utf-8') as f:
    f.write(html)
print('WROTE', map_html)
