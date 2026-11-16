#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

cd badminton_project
python manage.py collectstatic --no-input
python manage.py migrate --run-syncdb
python manage.py loaddata data.json