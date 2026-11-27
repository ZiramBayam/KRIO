#!/usr/bin/env bash
# Daily pg_dump of the KRIO database to the VM's persistent OS disk; keeps 7 copies.
set -euo pipefail
set -a; . /etc/krio/krio.env; set +a
dir=/var/backups/krio
mkdir -p "$dir"
file="$dir/krio-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --format=custom --no-owner --dbname="$DATABASE_URL" --file="$file.tmp"
mv "$file.tmp" "$file"
ls -1t "$dir"/krio-*.dump | tail -n +8 | xargs -r rm --
echo "backup ok: $file"
