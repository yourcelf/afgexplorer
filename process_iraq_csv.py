"""
This script processes the 'iraq-war-diary-redacted.csv' file to match the
format of the previously released Afghanistan war logs csv file.
"""

import csv
import itertools

with open("refactored.csv", 'w') as outfile:
    writer = csv.writer(outfile)
    with open("iraq-war-diary-redacted.csv") as infile:
        reader = csv.reader(infile, quotechar='"', escapechar='\\')
        for row in itertools.islice(reader, 1, None):
            writer.writerow(row[2:])

