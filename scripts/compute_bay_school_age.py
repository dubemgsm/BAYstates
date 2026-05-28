#!/usr/bin/env python3
import json, sys
from tifffile import TiffFile
import numpy as np

# inputs hardcoded for repo paths
age_dir = '/workspaces/BAYstates/data/age'
primary = f'{age_dir}/NGA_F_M_PRIMARY_2020_1km.tif'
secondary = f'{age_dir}/NGA_F_M_SECONDARY_2020_1km.tif'
# get bbox file
bounds_file = '/workspaces/BAYstates/data/raw/bay_bounds.json'

# read bounds
with open(bounds_file) as f:
    bounds = json.load(f)

# helper to read geotransform from TIFF
def read_geo(tifpath):
    with TiffFile(tifpath) as tif:
        page = tif.pages[0]
        tags = page.tags
        tie = None
        scale = None
        if 'ModelTiepointTag' in tags:
            tie = tags['ModelTiepointTag'].value
        if 'ModelPixelScaleTag' in tags:
            scale = tags['ModelPixelScaleTag'].value
        arr = page.asarray()
    return arr, tie, scale

p_arr, tie_p, scale_p = read_geo(primary)
s_arr, tie_s, scale_s = read_geo(secondary)
# assume same geotransform
tie = tie_p or tie_s
scale = scale_p or scale_s
if tie is None or scale is None:
    print('Missing geo tags; cannot map coordinates to pixels', file=sys.stderr)
    sys.exit(1)
# tie is a tuple like (i,j,k, x,y,z)
# use first tiepoint
i0,j0,k0,x0,y0,z0 = tie[0:6]
psx, psy, psz = scale[0:3]

# function to convert lon,lat to col,row
def lonlat_to_colrow(lon, lat):
    col = (lon - x0) / psx + i0
    row = (y0 - lat) / psy + j0
    return int(np.floor(col)), int(np.floor(row))

# compute totals
# mask nodata values (WorldPop uses -99999)
mask_nodata = lambda arr: np.where(arr < -90000, 0.0, arr)
p_arr = mask_nodata(p_arr.astype('float64'))
s_arr = mask_nodata(s_arr.astype('float64'))

total = p_arr + s_arr
results = []
for b in bounds:
    name = b['name']
    minlat = b['minlat']; minlon = b['minlon']; maxlat = b['maxlat']; maxlon = b['maxlon']
    c1,r1 = lonlat_to_colrow(minlon, maxlat)  # upper-left
    c2,r2 = lonlat_to_colrow(maxlon, minlat)  # lower-right
    # clip to array boundaries
    nrows, ncols = total.shape
    c1 = max(0, min(ncols-1, c1)); c2 = max(0, min(ncols-1, c2))
    r1 = max(0, min(nrows-1, r1)); r2 = max(0, min(nrows-1, r2))
    if c2 < c1: c1,c2 = c2,c1
    if r2 < r1: r1,r2 = r2,r1
    window = total[r1:r2+1, c1:c2+1]
    pop_sum = float(np.nansum(window))
    results.append({'state': name, 'population_5_17_approx': pop_sum})

out_file = '/workspaces/BAYstates/data/clean/bay_school_age_population_approx_2020.csv'
import csv
with open(out_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['state','population_5_17_approx'])
    writer.writeheader()
    for row in results:
        writer.writerow(row)
print('WROTE', out_file)
