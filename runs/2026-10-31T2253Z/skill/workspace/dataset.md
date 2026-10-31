# Taxi Trips (2013-2023)

## Description from the City of Chicago data portal

<b>This dataset ends with 2023. Please see the Featured Content link below for the dataset that starts in 2024.</b>

Taxi trips from 2013 to 2023 reported to the City of Chicago in its role as a regulatory agency.  To protect privacy but allow for aggregate analyses, the Taxi ID is consistent for any given taxi medallion number but does not show the number, Census Tracts are suppressed in some cases, and times are rounded to the nearest 15 minutes.

Due to the data reporting process, not all trips are reported but the City believes that most are.

## Columns

| Column | Type | Description |
|---|---|---|
| `trip_id` | text | A unique identifier for the trip. |
| `taxi_id` | text | A unique identifier for the taxi. |
| `trip_start_timestamp` | calendar_date | When the trip started, rounded to the nearest 15 minutes. |
| `trip_end_timestamp` | calendar_date | When the trip ended, rounded to the nearest 15 minutes. |
| `trip_seconds` | number | Time of the trip in seconds. |
| `trip_miles` | number | Distance of the trip in miles. |
| `pickup_census_tract` | text | The Census Tract where the trip began.  For privacy, this Census Tract is not shown for some trips. This column often will be blank for locations outside Chicago. |
| `dropoff_census_tract` | text | The Census Tract where the trip ended.  For privacy, this Census Tract is not shown for some trips. This column often will be blank for locations outside Chicago. |
| `pickup_community_area` | number | The Community Area where the trip began. This column will be blank for locations outside Chicago. |
| `dropoff_community_area` | number | The Community Area where the trip ended. This column will be blank for locations outside Chicago. |
| `fare` | number | The fare for the trip. |
| `tips` | number | The tip for the trip. Cash tips generally will not be recorded. |
| `tolls` | number | The tolls for the trip. |
| `extras` | number | Extra charges for the trip. |
| `trip_total` | number | Total cost of the trip, the total of the previous columns. |
| `payment_type` | text | Type of payment for the trip. |
| `company` | text | The taxi company. |
| `pickup_centroid_latitude` | number | The latitude of the center of the pickup census tract or the community area if the census tract has been hidden for privacy. This column often will be blank for locations outside Chicago. |
| `pickup_centroid_longitude` | number | The longitude of the center of the pickup census tract or the community area if the census tract has been hidden for privacy. This column often will be blank for locations outside Chicago. |
| `pickup_centroid_location` | point | The location of the center of the pickup census tract or the community area if the census tract has been hidden for privacy. This column often will be blank for locations outside Chicago. |
| `dropoff_centroid_latitude` | number | The latitude of the center of the dropoff census tract or the community area if the census tract has been hidden for privacy. This column often will be blank for locations outside Chicago. |
| `dropoff_centroid_longitude` | number | The longitude of the center of the dropoff census tract or the community area if the census tract has been hidden for privacy. This column often will be blank for locations outside Chicago. |
| `dropoff_centroid_location` | point | The location of the center of the dropoff census tract or the community area if the census tract has been hidden for privacy. This column often will be blank for locations outside Chicago. |

## The data you will receive

One week of trips, Monday 2023-09-11 to Sunday 2023-09-17: 135,768 rows, in a CSV file named `trips.csv` with the columns above.
