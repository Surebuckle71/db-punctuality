-- The two marts slice the same events differently; their monthly net totals must match.
with by_phase as (
    select service_month, sum(minutes_net) as net
    from {{ ref('fct_delay_by_phase') }}
    group by service_month
),

by_location as (
    select service_month, sum(minutes_net) as net
    from {{ ref('fct_delay_locations') }}
    group by service_month
)

select *
from by_phase p
full join by_location l using (service_month)
where p.net is distinct from l.net
