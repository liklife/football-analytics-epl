from pathlib import Path
import getpass
from urllib.request import urlretrieve

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "E0.csv"
CLEAN = ROOT / "data" / "processed" / "E0_clear.csv"
RESULTS = ROOT / "results"
SOURCE_URL = "https://www.football-data.co.uk/mmz4281/2526/E0.csv"
DATABASE = "football_analytics_demo"


def prepare_data():
    RAW.parent.mkdir(parents=True, exist_ok=True)
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        print(f"Downloading {SOURCE_URL}")
        try:
            urlretrieve(SOURCE_URL, RAW)
        except Exception as exc:
            raise RuntimeError(
                f"Could not download the source CSV. Check the URL: {SOURCE_URL}"
            ) from exc

    source = pd.read_csv(RAW)
    columns = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HS", "AS", "HST", "AST"]
    missing = sorted(set(columns) - set(source.columns))
    if missing:
        raise ValueError("Unexpected CSV format; missing columns: " + ", ".join(missing))

    df = source[columns].copy().rename(columns={
        "Date": "match_date", "HomeTeam": "home_team", "AwayTeam": "away_team",
        "FTHG": "home_goals", "FTAG": "away_goals", "HS": "home_shots",
        "AS": "away_shots", "HST": "home_shots_on_target", "AST": "away_shots_on_target",
    })
    df["match_date"] = pd.to_datetime(
        df["match_date"], format="%d/%m/%Y", errors="raise"
    ).dt.date
    numeric = [
        "home_goals", "away_goals", "home_shots", "away_shots",
        "home_shots_on_target", "away_shots_on_target",
    ]

    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df.empty or df[numeric].isna().any().any():
        raise ValueError("CSV is empty or has missing/non-numeric match statistics.")

    if (df[numeric] < 0).any().any():
        raise ValueError("Match statistics cannot contain negative values.")

    if (df["home_shots_on_target"] > df["home_shots"]).any():
        raise ValueError("Home shots on target cannot exceed total home shots.")

    if (df["away_shots_on_target"] > df["away_shots"]).any():
        raise ValueError("Away shots on target cannot exceed total away shots.")

    df.to_csv(CLEAN, index=False, encoding="utf-8-sig")
    print(f"Prepared {len(df)} matches; saved {CLEAN}")
    return df



def engine_for(database, password):
    return create_engine(URL.create(
        "postgresql+psycopg", username="postgres", password=password,
        host="localhost", port=5432, database=database,
    ), pool_pre_ping=True)


def ensure_database(password):
    admin = engine_for("postgres", password)
    try:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db"), {"db": DATABASE}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{DATABASE}"'))
                print(f"Created separate database {DATABASE}")
            else:
                print(f"Using separate database {DATABASE}")
    finally:
        admin.dispose()


def load_and_analyze(df, password):
    engine = engine_for(DATABASE, password)
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS matches_raw (
                    match_date DATE, home_team TEXT, away_team TEXT,
                    home_goals INTEGER, away_goals INTEGER,
                    home_shots INTEGER, away_shots INTEGER,
                    home_shots_on_target INTEGER, away_shots_on_target INTEGER
                )
            """))
            conn.execute(text("TRUNCATE TABLE matches_raw"))
            df.to_sql("matches_raw", conn, if_exists="append", index=False, method="multi")
            conn.execute(text("DROP TABLE IF EXISTS team_match_stats"))
            conn.execute(text("""
                CREATE TABLE team_match_stats AS
                SELECT match_date, home_team AS team, away_team AS opponent,
                       'Home' AS venue, home_goals AS goals, home_shots AS shots,
                       home_shots_on_target AS shots_on_target
                FROM matches_raw
                UNION ALL
                SELECT match_date, away_team AS team, home_team AS opponent,
                       'Away' AS venue, away_goals AS goals, away_shots AS shots,
                       away_shots_on_target AS shots_on_target
                FROM matches_raw
            """))

        result = pd.read_sql_query(text("""
            SELECT team, SUM(goals)::INTEGER AS total_goals,
                   SUM(shots)::INTEGER AS total_shots,
                   SUM(shots_on_target)::INTEGER AS total_shots_on_target
            FROM team_match_stats
            GROUP BY team ORDER BY total_goals DESC
        """), engine)
        if result.empty:
            raise ValueError("SQL analysis returned no rows.")
        result["shot_conversion_pct"] = (
            result["total_goals"] / result["total_shots"] * 100
        ).round(2)
        result["target_shot_pct"] = (
            result["total_shots_on_target"] / result["total_shots"] * 100
        ).round(2)
        result["goals_per_target_pct"] = (
            result["total_goals"] / result["total_shots_on_target"] * 100
        ).round(2)
        csv_path = RESULTS / "team_analysis.csv"
        result.to_csv(csv_path, index=False, encoding="utf-8-sig")

        ordered = result.sort_values("shot_conversion_pct")
        fig, ax = plt.subplots(figsize=(12, 9))
        bars = ax.barh(ordered["team"], ordered["shot_conversion_pct"])
        ax.bar_label(bars, fmt="%.2f%%", padding=4, fontsize=8)
        ax.set(title="EPL 2025/26: Shot conversion", xlabel="Goals / total shots, %", ylabel="Team")
        ax.grid(axis="x", alpha=0.25)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(RESULTS / "shot_conversion.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(13, 9))
        ax.scatter(result["total_shots"], result["total_goals"], s=65)
        for _, row in result.iterrows():
            ax.annotate(row["team"], (row["total_shots"], row["total_goals"]),
                        xytext=(6, 3), textcoords="offset points", fontsize=8)
        ax.set(title="EPL 2025/26: Total shots vs goals", xlabel="Total shots", ylabel="Goals")
        ax.grid(alpha=0.25)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(RESULTS / "shots_vs_goals.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

        print("\n=== EPL 2025/26 team analysis ===")
        print(result.to_string(index=False))
        print(f"\nSaved table: {csv_path}")
        print(f"Saved charts: {RESULTS / 'shot_conversion.png'} and {RESULTS / 'shots_vs_goals.png'}")
    finally:
        engine.dispose()


def main():
    print(f"Pipeline uses separate database '{DATABASE}'.")
    print("Your existing 'football_analytics' database will not be modified.")
    password = getpass.getpass("PostgreSQL password for user 'postgres': ")
    df = prepare_data()
    ensure_database(password)
    load_and_analyze(df, password)
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
