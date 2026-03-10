# Title
Aaron Jeung

#### Question
Are some airports more delay-prone and cause delays that propagate to later flights in the day? 

#### Hypothesis
Small airports should have a low rate of delays because there is less traffic at the airport. 
Large airports should have a low rate of delays because airlines use it as a hub, so airlines should be able to use their spare airplanes to better prevent delays. 
Therefore, I hypothesize mid-size airports to have the highest rate of delays.  

#### Dataset
I used flight data from the Department of Transportation's Bureau of Transportation Statistics. This dataset only contains US domestic flights. I particularly looked
at January 2023-November 2025 data, to exclude potential COVID anomalies. 
The dataset can be found here: https://www.transtats.bts.gov/Tables.asp?QO_VQ=EFD&QO_anzr=Nv4yv0r%FDb0-gvzr%FDcr4s14zn0pr%FDQn6n&QO_fu146_anzr=b0-gvzr

#### Results
I first looked at whether there was a correlation between airport size and how frequent delays occurred. 
![alttext](depDelayRate.png)

From this graph, we can see that the airports with more flights tend to have a higher rate of delayed departures. 

However, it is too early to conclude large airports are causing delays. During my analysis, I found that 53% of airplanes that arrive late also depart late for its next flight,
while 12% of airplanes that arrive on time depart late for its next flight. This means that it is almost 5 times more likely that a delay is due to the airplane arriving late 
instead of somee other cause

For the next part of my analysis, I looked at which airports are causing delays (which lead to further delays throughout the day). I called instances of an airplane arriving on time
but its next flight being delayed as sourceDelays, and analyzed which airports had the highest rate of sourceDelays. 
![alttext](sourceDelayRate.png)
