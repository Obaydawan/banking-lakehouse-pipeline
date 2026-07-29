-- Gold layer: flagged transactions
-- Applies three fraud detection rules:
--   1. Velocity fraud: 6+ transactions from the same account within a 30-minute window
--   2. Geographic anomaly: transaction originates from a higher-risk country
--   3. Statistical outlier: transaction amount is far above that account's typical spend

with txns as (
    select * from {{ ref('stg_transactions') }}
),

-- Rule 1: Velocity fraud — count transactions per account in a trailing 30-minute window
velocity as (
    select
        transaction_id,
        count(*) over (
            partition by account_id
            order by "timestamp"
            range between interval '30 minutes' preceding and current row
        ) as txns_in_30min
    from txns
),

-- Rule 2: Geographic anomaly — flag transactions from higher-risk countries
geo_flagged as (
    select
        transaction_id,
        case when country in ('NG', 'KP', 'IR') then true else false end as is_high_risk_country
    from txns
),

-- Rule 3: Statistical outlier — amount far above the account's own baseline.
-- Cold-start handling: accounts with fewer than 10 transactions don't have enough
-- history to establish a reliable personal baseline, so those fall back to a
-- global percentile threshold instead of a per-account stddev comparison.
global_stats as (
    select
        quantile_cont(amount, 0.995) as global_p995
    from txns
),

account_stats as (
    select
        account_id,
        avg(amount) as avg_amount,
        stddev(amount) as stddev_amount,
        count(*) as txn_count
    from txns
    group by account_id
),

outliers as (
    select
        t.transaction_id,
        case
            when a.txn_count >= 10
                 and a.stddev_amount is not null
                 and a.stddev_amount > 0
                 and t.amount > (a.avg_amount + 4 * a.stddev_amount)
                then true
            when a.txn_count < 10
                 and t.amount > g.global_p995
                then true
            else false
        end as is_amount_outlier
    from txns t
    left join account_stats a on t.account_id = a.account_id
    cross join global_stats g
),

combined as (
    select
        t.transaction_id,
        t.account_id,
        t."timestamp",
        t.amount,
        t.currency,
        t.merchant_category,
        t.transaction_type,
        t.country,
        coalesce(v.txns_in_30min >= 6, false) as is_velocity_flag,
        coalesce(g.is_high_risk_country, false) as is_geo_flag,
        coalesce(o.is_amount_outlier, false) as is_outlier_flag
    from txns t
    left join velocity v on t.transaction_id = v.transaction_id
    left join geo_flagged g on t.transaction_id = g.transaction_id
    left join outliers o on t.transaction_id = o.transaction_id
)

select
    *,
    (is_velocity_flag or is_geo_flag or is_outlier_flag) as is_flagged,
    (
        case when is_velocity_flag then 1 else 0 end +
        case when is_geo_flag then 1 else 0 end +
        case when is_outlier_flag then 1 else 0 end
    ) as flag_count
from combined
where is_velocity_flag or is_geo_flag or is_outlier_flag
