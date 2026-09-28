-- One row per train stop. Keeps every row; later models filter on the flags.
-- "reported" times are the latest DB forecast when the data was fetched,
-- which is usually but not always the final actual time.

with source as (
    select * from {{ source('raw', 'stops') }}
),

renamed as (
    select
        id                                                         as stop_id,
        train_line_ride_id || '-' || regexp_extract(id, '-([0-9]{10})-[0-9]+$', 1)
                                                                   as journey_id,
        train_line_station_num                                     as stop_seq,
        regexp_extract(filename, 'stops-([0-9]{4}-[0-9]{2})\.parquet$', 1)
                                                                   as service_month,
        eva,
        station_name,
        train_type,
        train_type || ' ' || train_number                          as train_label,
        arrival_planned_time                                       as arrival_planned,
        arrival_change_time                                        as arrival_reported,
        departure_planned_time                                     as departure_planned,
        departure_change_time                                      as departure_reported,
        date_diff('minute', arrival_planned_time, arrival_change_time)
                                                                   as arrival_delay_min,
        date_diff('minute', departure_planned_time, departure_change_time)
                                                                   as departure_delay_min,
        delay_in_min                                               as source_delay_min,
        arrival_is_canceled or departure_is_canceled               as is_cancelled,
        is_additional_stop,
        is_replacement_train
    from source
)

select
    *,
    -- delays far outside this window are mostly re-timed schedules, not real running
    coalesce(arrival_delay_min between -15 and 360, true)
        and coalesce(departure_delay_min between -15 and 360, true)
                                                                   as has_plausible_delay,
    coalesce(departure_reported >= arrival_reported, true)         as has_consistent_times
from renamed
