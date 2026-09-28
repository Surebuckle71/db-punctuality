-- One row per intermediate stop: delay added while the train stood at the station.
-- Origin and final stops have no dwell (no arrival or no departure).

select
    stop_id,
    journey_id,
    service_month,
    train_type,
    train_label,
    eva,
    station_name,
    arrival_planned,
    arrival_delay_min,
    departure_delay_min,
    departure_delay_min - arrival_delay_min as dwell_delay_added_min
from {{ ref('int_usable_stops') }}
where arrival_delay_min is not null
  and departure_delay_min is not null
