-- One row per pair of consecutive stops in a journey (a leg of track).
-- run_delay_added_min > 0 means the train lost time between the two stops.
-- Legs across a skipped or unusable stop are dropped, so delay is never misattributed.

with stops as (
    select * from {{ ref('int_usable_stops') }}
),

paired as (
    select
        journey_id,
        service_month,
        train_type,
        train_label,
        lag(stop_seq)            over w as from_seq,
        lag(eva)                 over w as from_eva,
        lag(station_name)        over w as from_station,
        lag(departure_planned)   over w as from_departure_planned,
        lag(departure_delay_min) over w as from_departure_delay_min,
        stop_seq                        as to_seq,
        eva                             as to_eva,
        station_name                    as to_station,
        arrival_planned                 as to_arrival_planned,
        arrival_delay_min               as to_arrival_delay_min
    from stops
    window w as (partition by journey_id order by stop_seq)
)

select
    journey_id || '-' || to_seq                          as leg_id,
    journey_id,
    service_month,
    train_type,
    train_label,
    from_eva,
    from_station,
    to_eva,
    to_station,
    from_departure_planned,
    to_arrival_planned,
    date_diff('minute', from_departure_planned, to_arrival_planned)
                                                         as scheduled_run_min,
    from_departure_delay_min,
    to_arrival_delay_min,
    to_arrival_delay_min - from_departure_delay_min      as run_delay_added_min
from paired
where from_seq = to_seq - 1
  and from_departure_delay_min is not null
  and to_arrival_delay_min is not null
