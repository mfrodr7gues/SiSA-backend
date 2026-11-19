#!/bin/sh
set -eu
sleep 35
while true; do
  python manage.py issue_certificates || true
  sleep 60
done
