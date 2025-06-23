import csv
from datetime import datetime, timedelta
from collections import Counter

heartrates = []
timestamps = []

with open("heart_rate.csv") as f:
    csvdata = csv.reader(f, delimiter=',', quotechar='"')
    next(csvdata)
    for row in csvdata:
        timestamps.append(datetime.strptime(row[0], '%Y-%m-%dT%H:%M:%S
            .%fZ'))
    heartrates.append(int(row[1]))

intervals = [(timestamps[i+1] - timestamps[i]).seconds for i in range(0, len(timestamps)-1)]
count = Counter(intervals)
default_interval, _ = count.most_common()[0]

for j, interval in enumerate(intervals):
    gapsum = 0
    delta = interval - default_interval
    if interval != default_interval:
        for i in range(1, interval-delta+1):
            offset = j + gapsum + i
            existing = timestamps[j + gapsum]
            print(offset, i, existing.second)
            timestamps.insert(offset,
                              datetime(existing.year,
                                       existing.month,
                                       existing.day,
                                       existing.hour,
                                       existing.minute,
                                       existing.second +i,
                                       existing.microsecond))
            heartrates.insert(offset, 'E')

    gapsum += delta
