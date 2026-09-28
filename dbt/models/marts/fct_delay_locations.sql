-- Every place where long-distance trains add delay, per month:
-- a directed track segment (A -> B) or a station stop.
-- minutes_gained counts only increases, so slack elsewhere does not hide lost time.

with track as (
    select
        service_month,
        'track'                                  as location_type,
        from_eva || '>' || to_eva                as location_key,
        from_station || ' → ' || to_station      as location_name,
        run_delay_added_min                      as added_min
    from {{ ref('int_journey_legs') }}
),

station as (
    select
        service_month,
        'station'                                as location_type,
        eva                                      as location_key,
        station_name                             as location_name,
        dwell_delay_added_min                    as added_min
    from {{ ref('int_station_dwells') }}
),

events as (
    select * from track
    union all
    select * from station
)

select
    service_month,
    location_type || ':' || location_key         as location_id,
    location_type,
    any_value(location_name)                     as location_name,
    count(*)                                     as n_train_passes,
    sum(greatest(added_min, 0))                  as minutes_gained,
    sum(least(added_min, 0))                     as minutes_recovered,
    sum(added_min)                               as minutes_net,
    avg((added_min >= 5)::int)                   as share_passes_gaining_5_plus
from events
group by service_month, location_type, location_key
