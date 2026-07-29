-- Silver layer: cleaned accounts
-- Handles: orphaned customer_id references (accounts pointing to non-existent customers)

with source as (
    select * from {{ source('bronze', 'bronze_accounts') }}
),

valid_customers as (
    select customer_id from {{ ref('stg_customers') }}
),

cleaned as (
    select
        a.account_id,
        a.customer_id,
        a.account_type,
        a.open_date,
        a.country,
        a.status,
        a._ingested_at
    from source a
    inner join valid_customers c
        on a.customer_id = c.customer_id
    where a.account_id is not null
)

select * from cleaned
