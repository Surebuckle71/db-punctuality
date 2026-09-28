-- For journeys where every stop is usable and consecutive, delay must add up exactly:
-- first departure delay + delay added on track + delay added at stations = final arrival delay.
-- Returns journeys where it does not.

with complete_journeys as (
    select journey_id
    from {{ ref('int_usable_stops') }}
    group by journey_id
    having count(*) = max(stop_seq) - min(stop_seq) + 1
       and count(*) >= 2
),

endpoints as (
    select
        journey_id,
        min(stop_seq)                          as first_seq,
        max(stop_seq)                          as last_seq,
        arg_min(departure_delay_min, stop_seq) as first_departure_delay,
        arg_max(arrival_delay_min, stop_seq)   as last_arrival_delay
    from {{ ref('int_usable_stops') }}
    where journey_id in (select journey_id from complete_journeys)
    group by journey_id
),

run as (
    select journey_id, sum(run_delay_added_min) as run_added
    from {{ ref('int_journey_legs') }}
    group by journey_id
),

-- only dwells strictly between the first departure and the last arrival count;
-- the first/last usable stop may have a real dwell that lies outside that window
dwell as (
    select d.journey_id, sum(d.dwell_delay_added_min) as dwell_added
    from {{ ref('int_station_dwells') }} d
    join {{ ref('int_usable_stops') }} s using (stop_id)
    join endpoints e on e.journey_id = d.journey_id
    where s.stop_seq > e.first_seq and s.stop_seq < e.last_seq
    group by d.journey_id
)

select e.*, r.run_added, d.dwell_added
from endpoints e
join run r using (journey_id)
left join dwell d using (journey_id)
where e.first_departure_delay is not null
  and e.last_arrival_delay is not null
  and e.first_departure_delay + r.run_added + coalesce(d.dwell_added, 0) != e.last_arrival_delay
