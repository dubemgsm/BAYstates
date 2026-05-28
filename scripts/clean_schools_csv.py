#!/usr/bin/env python3
import sys, csv

if len(sys.argv) < 3:
    print("Usage: clean_schools_csv.py input.csv output.csv [states_comma_separated]", file=sys.stderr)
    sys.exit(2)

inp, out = sys.argv[1], sys.argv[2]
states_arg = sys.argv[3] if len(sys.argv) > 3 else ''
states = {s.strip().lower() for s in states_arg.split(',') if s.strip()} if states_arg else set()

seen = set()
rows=[]
with open(inp, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        name = (r.get('name') or '').strip()
        lat = (r.get('latitude') or '').strip()
        lon = (r.get('longitude') or '').strip()
        typ = (r.get('type') or '').strip()
        state = (r.get('state') or '').strip()
        if not lat or not lon:
            continue
        try:
            latf = float(lat); lonf = float(lon)
        except:
            continue
        # If states filter provided, keep only matching states (case-insensitive). If state is empty, drop.
        if states:
            if not state or state.strip().lower() not in states:
                continue
        key = (name.lower(), round(latf,6), round(lonf,6))
        if key in seen:
            continue
        seen.add(key)
        rows.append({'name': name, 'latitude': f"{latf:.6f}", 'longitude': f"{lonf:.6f}", 'type': typ, 'state': state})

with open(out, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['name','latitude','longitude','type','state'])
    writer.writeheader()
    writer.writerows(rows)

print(f"WROTE {out} ({len(rows)} records)")
