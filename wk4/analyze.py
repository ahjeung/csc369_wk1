import polars as pl

df = pl.scan_parquet("2022_place_canvas_history.parquet")

# placing over 50 pixels, about 5 minutes apart from one another
df1 = df.sort('timestamp')\
        .group_by('user_id')\
        .agg([pl.col('timestamp').len().alias('numPixels'),
              pl.col('timestamp').diff().dt.total_seconds().mean().alias('meanTimeBetweenPixels')])\
        .filter((pl.col('numPixels') > 50) & (pl.col('meanTimeBetweenPixels') <= 305))\
        .collect()
print(f"There were {df1.height} users who placed more than 50 pixels, about 305 seconds apart:")
print(df1)

# placing over 50 pixels, mostly at the same coordinate
df2 = df.group_by('user_id')\
      .agg([pl.col('timestamp').len().alias('numPixels'),
            pl.col('coordinate').n_unique().alias('numUniqueCoord')])\
      .with_columns((pl.col('numUniqueCoord') / pl.col('numPixels')).alias('ratio'))\
      .filter((pl.col('numPixels') > 50) & (pl.col('ratio') < 0.05))\
      .collect()

print(f"There were {df2.height} users who placed more than 50 pixels, mostly at the same coordinate:")
print(df2)

