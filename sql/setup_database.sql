
-- 1. Create a table for raw match statistics
CREATE TABLE matches_raw (
    match_date DATE,
    home_team TEXT,
    away_team TEXT,
    home_goals INTEGER,
    away_goals INTEGER,
    home_shots INTEGER,
    away_shots INTEGER,
    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER
);

-- 2. Create team-level match statistics
CREATE TABLE team_match_stats AS
SELECT
    match_date,
    home_team AS team,
    away_team AS opponent,
    'Home' AS venue,
    home_goals AS goals,
    home_shots AS shots,
    home_shots_on_target AS shots_on_target
FROM matches_raw

UNION ALL

SELECT
    match_date,
    away_team AS team,
    home_team AS opponent,
    'Away' AS venue,
    away_goals AS goals,
    away_shots AS shots,
    away_shots_on_target AS shots_on_target
FROM matches_raw;
