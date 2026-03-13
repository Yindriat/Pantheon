#!/bin/bash
set -e

echo "Converting pantheon.xlsx to pantheon.csv..."
python3 /docker-entrypoint-initdb.d/convert_xlsx.py

echo "SQL init will be automatically executed by Docker entrypoint (setup.sql)..."
