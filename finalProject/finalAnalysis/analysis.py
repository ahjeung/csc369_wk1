import polars as pl
import matplotlib.pyplot as plt

df = pl.scan_parquet('flightData23-25.parquet')

carrierCount = df.select(pl.col('OP_UNIQUE_CARRIER').value_counts(sort=True)).collect()
print(carrierCount)

# Find rate of non-diverted, non-cancelled flights that departed/arrived late from each airport in dataset
depDelay = df.group_by('ORIGIN_AIRPORT_ID').agg(
    [pl.len().alias('numDepartures'),
     (pl.col('DEP_DEL_15') == True).sum().alias('numDepDelays')]
    ).filter(
        pl.col('numDepartures') > pl.col('numDepartures').median()
    ).with_columns(
        (pl.col('numDepDelays') / pl.col('numDepartures')).alias('depDelPercentage')
    ).sort('depDelPercentage', descending=True).collect() 

numDeparturesList = depDelay['numDepartures'].to_list()
depDelayList = depDelay['depDelPercentage'].to_list()
plt.scatter(x=numDeparturesList, y=depDelayList)
plt.title('Departure Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Departure Delay Rate')
plt.xscale('log')
plt.savefig('depDelayRate.png')
plt.close()

arrDelay = df.group_by('DEST_AIRPORT_ID').agg(
    [pl.len().alias('numArrivals'),
     (pl.col('ARR_DEL_15') == True).sum().alias('numArrDelays')]
    ).filter(
        pl.col('numArrivals') > pl.col('numArrivals').median()
    ).with_columns(
        (pl.col('numArrDelays') / pl.col('numArrivals')).alias('arrDelPercentage')
    ).sort('arrDelPercentage', descending=True).collect() 

# See if airports with more frequent departure delays have more frequent arrival delays
depArrDelay = depDelay.join(arrDelay, left_on='ORIGIN_AIRPORT_ID', right_on='DEST_AIRPORT_ID')
depDelayList = depArrDelay['depDelPercentage'].to_list()
arrDelayList = depArrDelay['arrDelPercentage'].to_list()
plt.scatter(x=depDelayList, y=arrDelayList)
plt.title('Departure and Arrival Delay Rates of Top 180 Busiest Airports')
plt.xlabel('Departure Delay Rate')
plt.ylabel('Arrival Delay Rate')
plt.savefig('depArrDelayRates.png')
plt.close()

delayPropagation = df.select(['TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .sort(['TAIL_NUM', 'FL_DATE', 'DEP_TIME'])\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())

print(delayPropagation)
# See how often if a plane arrives late, its next flight also departs late 
tailNumDelayPropagation = delayPropagation\
    .select([
        pl.col('prevArrDel15').sum().alias('numPrevDelay'), # Number of flights where previous flight arrived late
        ((pl.col('prevArrDel15')==True) & (pl.col('DEP_DEL_15')==True)).sum().alias('numPrevAndCurDelay')])\
    .with_columns((pl.col('numPrevAndCurDelay') / pl.col('numPrevDelay')).alias("cuz")).collect()
print(tailNumDelayPropagation) # 52.84%

# See the other case: if a plane arrives on time, but its next flight departs late. 
tailNumDelayPropagation = delayPropagation\
    .select([
        (pl.col('prevArrDel15') == False).sum().alias('numPrevOnTime'), # Number of flights where previous flight arrived on time
        ((pl.col('prevArrDel15')==False) & (pl.col('DEP_DEL_15')==True)).sum().alias('numSourceDelay')])\
    .with_columns((pl.col('numSourceDelay') / pl.col('numPrevOnTime')).alias("cuz")).collect()
print(tailNumDelayPropagation) # 11.70%


# See which airport has the most occurences (by rate) of a plane arriving on time but its next flight departs late
airportDelayPropagation = delayPropagation.with_columns([
        ((pl.col('prevArrDel15') == False) & (pl.col('DEP_DEL_15') == True)).alias('sourceDelay'),
        (pl.col('prevArrDel15') == False).alias('arrOnTime')])\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('sourceDelay').sum().alias('numSourceDelay'),
        pl.col('arrOnTime').sum().alias('numArrOnTime')
        ])\
    .with_columns((pl.col('numSourceDelay') / pl.col('numArrOnTime')).alias('sourceDelayPercentage'))\
    .sort('sourceDelayPercentage', descending=True)\
    .filter(pl.col('numDepartures') > pl.col('numDepartures').median())\
    .collect()

numDeparturesList = airportDelayPropagation['numDepartures'].to_list()
sourceDelayList = airportDelayPropagation['sourceDelayPercentage'].to_list()
plt.scatter(x=numDeparturesList, y=sourceDelayList)
plt.title('Source Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Source Delay Rate')
plt.xscale('log')
plt.savefig('sourceDelayRate.png')
plt.close()

print(airportDelayPropagation)

# See which airport has the most occurences (by rate) of a plane arriving on late but its next flight departs on time
airportDelayPropagation = delayPropagation.with_columns(
        ((pl.col('prevArrDel15') == True) & (pl.col('DEP_DEL_15') == False)).alias('correctDelay'))\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('prevArrDel15').sum().alias('numDelays'),
        pl.col('correctDelay').sum().alias('numCorrectDelay')])\
    .with_columns((pl.col('numCorrectDelay') / pl.col('numDelays')).alias('correctDelayPercentage'))\
    .sort('correctDelayPercentage', descending=True)\
    .filter(pl.col('numDepartures') > pl.col('numDepartures').median())\
    .collect()

correctDelayList = airportDelayPropagation['correctDelayPercentage'].to_list()
numDeparturesList = airportDelayPropagation['numDepartures'].to_list()
plt.scatter(x=numDeparturesList, y=correctDelayList)
plt.title('Correct Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Correct Delay Rate')
plt.xscale('log')
plt.savefig('correctDelayRate.png')
plt.close()
print(airportDelayPropagation)


# Only look at WN (Southwest), DL (Delta), AA (American)

### Southwest Airlines

WNDepDelay = df.filter(
    pl.col('OP_UNIQUE_CARRIER') == 'WN')\
    .group_by('ORIGIN_AIRPORT_ID').agg(
    [pl.len().alias('numDepartures'),
     (pl.col('DEP_DEL_15') == True).sum().alias('numDepDelays')]
    ).filter(
        pl.col('numDepartures') > 1000 # Used to be .filter(pl.col('numDepartures) > pl.col('numDepartures).median())
    ).with_columns(
        (pl.col('numDepDelays') / pl.col('numDepartures')).alias('depDelPercentage')
    ).sort('depDelPercentage', descending=True).collect() 

WNnumDeparturesList = WNDepDelay['numDepartures'].to_list()
WNdepDelayList = WNDepDelay['depDelPercentage'].to_list()
plt.scatter(x=WNnumDeparturesList, y=WNdepDelayList)
plt.title('Departure Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Departure Delay Rate')
plt.xscale('log')
plt.savefig('WNdepDelayRate.png')
plt.close()


# See which airport has the most occurences (by rate) of a plane arriving on time but its next flight departs late
WNDelayPropagation = df.select(['OP_UNIQUE_CARRIER', 'TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .filter(pl.col('OP_UNIQUE_CARRIER') == 'WN')\
    .sort(['TAIL_NUM', 'FL_DATE', 'DEP_TIME'])\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())\
    .with_columns(
        [((pl.col('prevArrDel15') == False) & (pl.col('DEP_DEL_15') == True)).alias('sourceDelay'),
         (pl.col('prevArrDel15') == False).alias('arrOnTime')])\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('sourceDelay').sum().alias('numSourceDelay'), 
        pl.col('arrOnTime').sum().alias('numArrOnTime')])\
    .with_columns((pl.col('numSourceDelay') / pl.col('numArrOnTime')).alias('sourceDelayPercentage'))\
    .sort('sourceDelayPercentage', descending=True)\
    .filter(pl.col('numArrOnTime') > 1000)\
    .collect()

WNSourceDelayList = WNDelayPropagation['sourceDelayPercentage'].to_list()
WNnumDeparturesList = WNDelayPropagation['numDepartures'].to_list()
plt.scatter(x=WNnumDeparturesList, y=WNSourceDelayList)
plt.title('Source Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Source Delay Rate')
plt.xscale('log')
plt.savefig('WNsourceDelayRate.png')
plt.close()

# See which airport has the most occurences (by rate) of a plane arriving late but its next flight departs on time
WNDelayPropagation = df.select(['OP_UNIQUE_CARRIER', 'TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .filter(pl.col('OP_UNIQUE_CARRIER') == 'WN')\
    .sort(['TAIL_NUM', 'FL_DATE', 'DEP_TIME'])\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())\
    .with_columns(
        ((pl.col('prevArrDel15') == True) & (pl.col('DEP_DEL_15') == False)).alias('correctDelay'))\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('prevArrDel15').sum().alias('numDelays'),
        pl.col('correctDelay').sum().alias('numCorrectDelay')])\
    .with_columns((pl.col('numCorrectDelay') / pl.col('numDelays')).alias('correctDelayPercentage'))\
    .sort('correctDelayPercentage', descending=True)\
    .filter(pl.col('numDelays') > 1000)\
    .collect()

WNcorrectDelayList = WNDelayPropagation['correctDelayPercentage'].to_list()
WNnumDeparturesList = WNDelayPropagation['numDepartures'].to_list()
plt.scatter(x=WNnumDeparturesList, y=WNcorrectDelayList)
plt.title('Correct Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Correct Delay Rate')
plt.xscale('log')
plt.savefig('WNcorrectDelayRate.png')
plt.close()


### Delta Airlines

DLDepDelay = df.filter(
    pl.col('OP_UNIQUE_CARRIER') == 'DL')\
    .group_by('ORIGIN_AIRPORT_ID').agg(
    [pl.len().alias('numDepartures'),
     (pl.col('DEP_DEL_15') == True).sum().alias('numDepDelays')]
    ).filter(
        pl.col('numDepartures') > 1000
    ).with_columns(
        (pl.col('numDepDelays') / pl.col('numDepartures')).alias('depDelPercentage')
    ).sort('depDelPercentage', descending=True).collect() 

DLnumDeparturesList = DLDepDelay['numDepartures'].to_list()
DLdepDelayList = DLDepDelay['depDelPercentage'].to_list()
plt.scatter(x=DLnumDeparturesList, y=DLdepDelayList)
plt.title('Departure Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Departure Delay Rate')
plt.xscale('log')
plt.savefig('DLdepDelayRate.png')
plt.close()

# See which airport has the most occurences (by rate) of a plane arriving on time but its next flight departs late
DLDelayPropagation = df.select(['OP_UNIQUE_CARRIER', 'TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .filter(pl.col('OP_UNIQUE_CARRIER') == 'DL')\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())\
    .with_columns(
        [((pl.col('prevArrDel15') == False) & (pl.col('DEP_DEL_15') == True)).alias('sourceDelay'),
         (pl.col('prevArrDel15') == False).alias('arrOnTime')])\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('sourceDelay').sum().alias('numSourceDelay'), 
        pl.col('arrOnTime').sum().alias('numArrOnTime')])\
    .with_columns((pl.col('numSourceDelay') / pl.col('numArrOnTime')).alias('sourceDelayPercentage'))\
    .sort('sourceDelayPercentage', descending=True)\
    .filter(pl.col('numArrOnTime') > 1000)\
    .collect()

DLSourceDelayList = DLDelayPropagation['sourceDelayPercentage'].to_list()
DLnumDeparturesList = DLDelayPropagation['numDepartures'].to_list()
plt.scatter(x=DLnumDeparturesList, y=DLSourceDelayList)
plt.title('Source Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Source Delays Rate')
plt.xscale('log')
plt.savefig('DLsourceDelayRate.png')
plt.close()

# See which airport has the most occurences (by rate) of a plane arriving late but its next flight departs on time
DLDelayPropagation = df.select(['OP_UNIQUE_CARRIER', 'TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .filter(pl.col('OP_UNIQUE_CARRIER') == 'DL')\
    .sort(['TAIL_NUM', 'FL_DATE', 'DEP_TIME'])\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())\
    .with_columns(
        ((pl.col('prevArrDel15') == True) & (pl.col('DEP_DEL_15') == False)).alias('correctDelay'))\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('prevArrDel15').sum().alias('numDelays'),
        pl.col('correctDelay').sum().alias('numCorrectDelay')])\
    .with_columns((pl.col('numCorrectDelay') / pl.col('numDelays')).alias('correctDelayPercentage'))\
    .sort('correctDelayPercentage', descending=True)\
    .filter(pl.col('numDelays') > 1000)\
    .collect()

DLcorrectDelayList = DLDelayPropagation['correctDelayPercentage'].to_list()
DLnumDeparturesList = DLDelayPropagation['numDepartures'].to_list()
plt.scatter(x=DLnumDeparturesList, y=DLcorrectDelayList)
plt.title('Correct Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Correct Delay Rate')
plt.xscale('log')
plt.savefig('DLcorrectDelayRate.png')
plt.close()

### American Airlines

AADepDelay = df.filter(
    pl.col('OP_UNIQUE_CARRIER') == 'AA')\
    .group_by('ORIGIN_AIRPORT_ID').agg(
    [pl.len().alias('numDepartures'),
     (pl.col('DEP_DEL_15') == True).sum().alias('numDepDelays')]
    ).filter(
        pl.col('numDepartures') > 1000
    ).with_columns(
        (pl.col('numDepDelays') / pl.col('numDepartures')).alias('depDelPercentage')
    ).sort('depDelPercentage', descending=True).collect() 

AAnumDeparturesList = AADepDelay['numDepartures'].to_list()
AAdepDelayList = AADepDelay['depDelPercentage'].to_list()
plt.scatter(x=AAnumDeparturesList, y=AAdepDelayList)
plt.title('Departure Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Departure Delay Rate')
plt.xscale('log')
plt.savefig('AAdepDelayRate.png')
plt.close()

# See which airport has the most occurences (by rate) of a plane arriving on time but its next flight departs late
AADelayPropagation = df.select(['OP_UNIQUE_CARRIER', 'TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .filter(pl.col('OP_UNIQUE_CARRIER') == 'AA')\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())\
    .with_columns(
        [((pl.col('prevArrDel15') == False) & (pl.col('DEP_DEL_15') == True)).alias('sourceDelay'),
         (pl.col('prevArrDel15') == False).alias('arrOnTime')])\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('sourceDelay').sum().alias('numSourceDelay'), 
        pl.col('arrOnTime').sum().alias('numArrOnTime')])\
    .with_columns((pl.col('numSourceDelay') / pl.col('numArrOnTime')).alias('sourceDelayPercentage'))\
    .sort('sourceDelayPercentage', descending=True)\
    .filter(pl.col('numArrOnTime') > 1000)\
    .collect()

AASourceDelayList = AADelayPropagation['sourceDelayPercentage'].to_list()
AAnumDeparturesList = AADelayPropagation['numDepartures'].to_list()
plt.scatter(x=AAnumDeparturesList, y=AASourceDelayList)
plt.title('Source Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Source Delay Rate')
plt.xscale('log')
plt.savefig('AAsourceDelayRate.png')
plt.close()

# See which airport has the most occurences (by rate) of a plane arriving late but its next flight departs on time
AADelayPropagation = df.select(['OP_UNIQUE_CARRIER', 'TAIL_NUM', 'FL_DATE', 'DEP_TIME', 'ARR_DEL_15', 'DEP_DEL_15', 'ORIGIN_AIRPORT_ID'])\
    .filter(pl.col('OP_UNIQUE_CARRIER') == 'AA')\
    .sort(['TAIL_NUM', 'FL_DATE', 'DEP_TIME'])\
    .with_columns(
        pl.col('ARR_DEL_15')
        .shift(1)
        .over("TAIL_NUM")
        .alias("prevArrDel15")
    ).filter(pl.col("prevArrDel15").is_not_null())\
    .with_columns(
        ((pl.col('prevArrDel15') == True) & (pl.col('DEP_DEL_15') == False)).alias('correctDelay'))\
    .group_by('ORIGIN_AIRPORT_ID')\
    .agg([
        pl.len().alias('numDepartures'),
        pl.col('prevArrDel15').sum().alias('numDelays'),
        pl.col('correctDelay').sum().alias('numCorrectDelay')])\
    .with_columns((pl.col('numCorrectDelay') / pl.col('numDelays')).alias('correctDelayPercentage'))\
    .sort('correctDelayPercentage', descending=True)\
    .filter(pl.col('numDelays') > 1000)\
    .collect()

AAcorrectDelayList = AADelayPropagation['correctDelayPercentage'].to_list()
AAnumDeparturesList = AADelayPropagation['numDepartures'].to_list()
plt.scatter(x=AAnumDeparturesList, y=AAcorrectDelayList)
plt.title('Correct Delay Rate vs Number of Departures')
plt.xlabel('Number of Departures')
plt.ylabel('Correct Delay Rate')
plt.xscale('log')
plt.savefig('AAcorrectDelayRate.png')
plt.close()


# causeDelay = df.filter(pl.col('OP_UNIQUE_CARRIER') == 'AA').group_by('ORIGIN_AIRPORT_ID').agg([
#     pl.len().alias('numDepartures'),
#     pl.col('CARRIER_DELAY').mean().alias('CARRIER_DELAY_AVG'),
#     pl.col('WEATHER_DELAY').mean().alias('WEATHER_DELAY_AVG'),
#     pl.col('NAS_DELAY').mean().alias('NAS_DELAY_AVG'),
#     pl.col('SECURITY_DELAY').mean().alias('SECURITY_DELAY_AVG'),
#     pl.col('LATE_AIRCRAFT_DELAY').mean().alias('LATE_AIRCRAFT_DELAY_AVG')
# ]).collect()

# numDeparturesList = causeDelay['numDepartures'].to_list()
# causeDelayList = causeDelay['NAS_DELAY_AVG'].to_list()
# plt.scatter(x=numDeparturesList, y=causeDelayList)
# plt.title('NAS delay avg vs Number of Departures')
# plt.xlabel('Number of Departures')
# plt.ylabel('NAS delay avg')
# plt.xscale('log')
# plt.savefig('NASDelayAvg.png')
# plt.close()

# print(causeDelay)