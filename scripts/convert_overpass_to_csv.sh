#!/usr/bin/env bash
set -e
input="$1"
output="$2"
# Optional third arg (not used here): comma-separated states list. Filtering is handled in the cleaning step.
if [ -z "$input" ] || [ -z "$output" ]; then echo "Usage: $0 input.json output.csv" >&2; exit 2; fi
# output includes state extracted from tags when available
echo 'name,latitude,longitude,type,state' > "$output"
jq -r '.elements[] |
  (.tags.name // "") as $name |
  (.lat // .center.lat // null) as $lat |
  (.lon // .center.lon // null) as $lon |
  (.tags.amenity // .tags["GNS:dsg_string"] // .tags["school:type"] // "") as $type |
  (.tags["addr:state"] // .tags["is_in:state"] // .tags["is_in:province"] // "") as $state |
  if $lat == null or $lon == null then empty else [$name, ($lat|tostring), ($lon|tostring), $type, $state] end | @csv' "$input" >> "$output"
