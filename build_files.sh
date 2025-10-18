#!/bin/bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --no-cache-dir
python manage.py collectstatic --noinput