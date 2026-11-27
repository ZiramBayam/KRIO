#!/usr/bin/env bash
# Run on the VM as user krio: pull main, update backend, migrate, rebuild the
# dashboard, install unit files and restart. Safe to run repeatedly.
set -euo pipefail
cd /home/krio/KRIO
git fetch --quiet origin
git checkout --quiet "${1:-main}"
git pull --quiet --ff-only
.venv/bin/pip install --quiet -r requirements.txt
set -a; . /etc/krio/krio.env; set +a
.venv/bin/python -m alembic -c services/ingest/alembic.ini upgrade head
(cd apps/web && npm ci --silent && npm run build --silent)
sudo rsync -a --delete apps/web/out/ /var/www/krio/
sudo install -m 644 infra/vm/*.service infra/vm/*.timer /etc/systemd/system/
sudo install -m 644 infra/vm/nginx-krio.conf /etc/nginx/sites-available/krio
sudo ln -sf /etc/nginx/sites-available/krio /etc/nginx/sites-enabled/krio
sudo systemctl daemon-reload
sudo systemctl enable --quiet --now krio-backup.timer krio-partitions.timer
sudo systemctl restart krio-api
sudo nginx -t && sudo systemctl reload nginx
sleep 3
curl -fsS http://127.0.0.1/api/health && echo " deploy ok"
