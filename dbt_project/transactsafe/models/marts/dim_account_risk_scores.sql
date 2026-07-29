-- Gold layer: account-level risk scoring
-- Aggregates flagged transactions per account into a single risk score,
-- so a fraud analyst can prioritize which accounts to investigate first.

with flagged as (
    select * from {{ ref('fct_flagged_transactions') }}
),

all_txns as (
    select * from {{ ref('stg_transactions') }}
),

account_flag_summary as (
    select
        account_id,
        count(*) as total_flagged_transactions,
        sum(case when is_velocity_flag then 1 else 0 end) as velocity_flags,
        sum(case when is_geo_flag then 1 else 0 end) as geo_flags,
        sum(case when is_outlier_flag then 1 else 0 end) as outlier_flags,
        sum(flag_count) as total_flag_weight
    from flagged
    group by account_id
),

account_activity as (
    select
        account_id,
        count(*) as total_transactions,
        sum(amount) as total_amount
    from all_txns
    group by account_id
),

scored as (
    select
        a.account_id,
        coalesce(f.total_flagged_transactions, 0) as total_flagged_transactions,
        coalesce(f.velocity_flags, 0) as velocity_flags,
        coalesce(f.geo_flags, 0) as geo_flags,
        coalesce(f.outlier_flags, 0) as outlier_flags,
        a.total_transactions,
        a.total_amount,
        -- Risk score: presence-based severity weighting.
        -- Each rule contributes a fixed weight if it fires at all on this account,
        -- rather than being diluted by the account's total transaction volume.
        -- This reflects that even a small burst of fraud matters, regardless of
        -- how much normal activity surrounds it.
        least(
            100,
            (case when coalesce(f.velocity_flags, 0) > 0 then 55 else 0 end) +
            (case when coalesce(f.geo_flags, 0) > 0 then 35 else 0 end) +
            (case when coalesce(f.outlier_flags, 0) > 0 then 15 else 0 end)
        ) as risk_score
    from account_activity a
    left join account_flag_summary f on a.account_id = f.account_id
)

select
    *,
    case
        when risk_score >= 50 then 'High'
        when risk_score >= 20 then 'Medium'
        when risk_score > 0 then 'Low'
        else 'None'
    end as risk_tier
from scored
