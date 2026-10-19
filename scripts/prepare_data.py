
from pathlib import Path

import pandas as pd


# Define project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_DIR / "data" / "raw" / "E0.csv"
PROCESSED_DATA_PATH = PROJECT_DIR / "data" / "processed" / "E0_clear.csv"


# 1. Load the raw data
df = pd.read_csv(RAW_DATA_PATH)

# 2. Keep the required columns
columns = [
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "HS",
    "AS",
    "HST",
    "AST",
]

df_clear = df[columns].copy()

# 3. Rename columns
df_clear = df_clear.rename(
    columns={
        "Date": "match_date",
        "HomeTeam": "home_team",
        "AwayTeam": "away_team",
        "FTHG": "home_goals",
        "FTAG": "away_goals",
        "HS": "home_shots",
        "AS": "away_shots",
        "HST": "home_shots_on_target",
        "AST": "away_shots_on_target",
    }
)

# 4. Convert dates to YYYY-MM-DD
df_clear["match_date"] = pd.to_datetime(
    df_clear["match_date"],
    format="%d/%m/%Y",
)

df_clear["match_date"] = df_clear["match_date"].dt.strftime("%Y-%m-%d")

# 5. Validate the result
print("First five rows:")
print(df_clear.head())

print("\nDataset information:")
df_clear.info()

print(f"\nNumber of matches: {len(df_clear)}")
print(f"Missing values: {df_clear.isna().sum().sum()}")

# 6. Save the cleaned data
df_clear.to_csv(PROCESSED_DATA_PATH, index=False, encoding="utf-8-sig")

print(f"\nFile saved: {PROCESSED_DATA_PATH}")
