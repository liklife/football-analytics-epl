
-- 1. Top 10 teams by goals scored
SELECT
    team,
    SUM(goals) AS total_goals
FROM team_match_stats
GROUP BY team
ORDER BY total_goals DESC
LIMIT 10;


-- 2. Shot conversion rate
SELECT
    team,
    SUM(goals) AS total_goals,
    SUM(shots) AS total_shots,
    ROUND(
        SUM(goals)::numeric / NULLIF(SUM(shots), 0) * 100,
        2
    ) AS shot_conversion_pct
FROM team_match_stats
GROUP BY team
ORDER BY shot_conversion_pct DESC;


-- 3. Share of shots on target
SELECT
    team,
    SUM(shots) AS total_shots,
    SUM(shots_on_target) AS total_shots_on_target,
    ROUND(
        SUM(shots_on_target)::numeric
        / NULLIF(SUM(shots), 0) * 100,
        2
    ) AS target_shot_pct
FROM team_match_stats
GROUP BY team
ORDER BY target_shot_pct DESC;


-- 4. Overall season statistics and efficiency metrics
SELECT
    team,
    SUM(goals) AS total_goals,
    SUM(shots) AS total_shots,
    SUM(shots_on_target) AS total_shots_on_target,
    ROUND(
        SUM(shots_on_target)::numeric
        / NULLIF(SUM(shots), 0) * 100,
        2
    ) AS target_shot_pct,
    ROUND(
        SUM(goals)::numeric
        / NULLIF(SUM(shots), 0) * 100,
        2
    ) AS shot_conversion_pct,
    ROUND(
        SUM(goals)::numeric
        / NULLIF(SUM(shots_on_target), 0) * 100,
        2
    ) AS goals_per_target_pct
FROM team_match_stats
GROUP BY team
ORDER BY total_goals DESC;


-- 5. Shots not on target
-- This category may include blocked shots.
WITH team_shots AS (
    SELECT
        team,
        SUM(shots) AS total_shots,
        SUM(shots_on_target) AS total_shots_on_target
    FROM team_match_stats
    GROUP BY team
)
SELECT
    team,
    total_shots - total_shots_on_target AS shots_not_on_target,
    ROUND(
        (total_shots - total_shots_on_target)::numeric
        / NULLIF(total_shots, 0) * 100,
        2
    ) AS shots_not_on_target_pct
FROM team_shots
ORDER BY shots_not_on_target_pct DESC;
