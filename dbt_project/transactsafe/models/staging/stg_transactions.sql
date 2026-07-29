-- Silver layer: cleaned transactions
-- Handles: duplicate transaction_ids, null amounts, negative amounts, orphaned account_id references

with source as (
    select * from {{ source('bronze', 'bronze_transactions') }}
),

-- Deduplicate on transaction_id, keeping the earliest-ingested copy
deduplicated as (
    select *,
        row_number() over (
            partition by transaction_id
            order by _ingested_at asc
        ) as _row_num
    from source
),

valid_accounts as (
    select account_id from {{ ref('stg_accounts') }}
),

cleaned as (
    select
        d.transaction_id,
        d.account_id,
        d.timestamp,
        d.amount,
        d.currency,
        d.merchant_category,
        d.transaction_type,
        d.country,
        d._ingested_at
    from deduplicated d
    inner join valid_accounts a
        on d.account_id = a.account_id
    where d._row_num = 1               -- drop duplicate transaction_ids
      and d.amount is not null         -- drop null amounts
      and d.amount > 0                 -- drop negative/zero amounts (data quality issue)
      and d.transaction_id is not null
)

select * from cleaned
