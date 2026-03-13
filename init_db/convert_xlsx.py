#!/usr/bin/env python3
"""Convert pantheon.xlsx to pantheon.csv for PostgreSQL COPY import."""
import openpyxl
import csv
import sys

XLSX_PATH = "/docker-entrypoint-initdb.d/pantheon.xlsx"
CSV_PATH = "/tmp/pantheon.csv"

wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
ws = wb.active

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    for row in ws.iter_rows(values_only=True):
        writer.writerow(row)

wb.close()
print(f"Converted {XLSX_PATH} -> {CSV_PATH}")
