-- Silver layer: cleaned, deduplicated customers
-- Handles: exact duplicate rows, missing names

with source as (
    select * from {{ source('bronze', 'bronze_customers') }}
),

deduplicated as (
    select distinct * from source
),

cleaned as (
    select
        customer_id,
        coalesce(name, 'UNKNOWN') as name,
        country,
        signup_date,
        risk_profile_seed,
        _ingested_at
    from deduplicated
    where customer_id is not null
)

select * from cleaned
