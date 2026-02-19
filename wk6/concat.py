import csv
import glob

files = glob.glob("*.csv")
writeFile = "flightData23-25.csv"

with open(writeFile, 'w', newline='') as outFile:
    writer = csv.writer(outFile)
    for i, fname in enumerate(files):
        with open(fname, 'r') as infile:
            reader = csv.reader(infile)
            header = next(reader)
            if i == 0:
                writer.writerow(header)
            writer.writerows(reader)
