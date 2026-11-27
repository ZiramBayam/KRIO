#!/usr/bin/env bash
# Create readings partitions for this month and the next two, ahead of data.
# Must run before rows for a month land in readings_default, or PostgreSQL
# refuses to attach the new partition over those rows.
set -euo pipefail
set -a; . /etc/krio/krio.env; set +a
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -qc "
SELECT create_readings_partition((date_trunc('month', now()) + make_interval(months => m))::date)
FROM generate_series(0, 2) AS m;"
echo "partitions ok"
