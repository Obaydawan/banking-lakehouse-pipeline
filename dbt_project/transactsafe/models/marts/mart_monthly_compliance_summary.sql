-- Gold layer: monthly compliance summary
-- A rollup table designed for a compliance report: transaction volume,
-- flagged activity, and risk distribution by month.

with txns as (
    select * from {{ ref('stg_transactions') }}
),

flagged as (
    select * from {{ ref('fct_flagged_transactions') }}
),

monthly_activity as (
    select
        date_trunc('month', "timestamp") as month,
        count(*) as total_transactions,
        sum(amount) as total_transaction_volume,
        count(distinct account_id) as active_accounts
    from txns
    group by 1
),

monthly_flags as (
    select
        date_trunc('month', "timestamp") as month,
        count(*) as total_flagged_transactions,
        sum(case when is_velocity_flag then 1 else 0 end) as velocity_flags,
        sum(case when is_geo_flag then 1 else 0 end) as geo_flags,
        sum(case when is_outlier_flag then 1 else 0 end) as outlier_flags,
        count(distinct account_id) as flagged_accounts
    from flagged
    group by 1
)

select
    a.month,
    a.total_transactions,
    a.total_transaction_volume,
    a.active_accounts,
    coalesce(f.total_flagged_transactions, 0) as total_flagged_transactions,
    coalesce(f.velocity_flags, 0) as velocity_flags,
    coalesce(f.geo_flags, 0) as geo_flags,
    coalesce(f.outlier_flags, 0) as outlier_flags,
    coalesce(f.flagged_accounts, 0) as flagged_accounts,
    round(
        coalesce(f.total_flagged_transactions, 0)::float / nullif(a.total_transactions, 0) * 100,
        3
    ) as flagged_rate_pct
from monthly_activity a
left join monthly_flags f on a.month = f.month
order by a.month
