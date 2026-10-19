
from pathlib import Path
import getpass

import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import URL, create_engine


# Пути проекта
PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    # 1. Подключение к PostgreSQL
    password = getpass.getpass("Пароль PostgreSQL: ")

    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username="postgres",
        password=password,
        host="localhost",
        port=5432,
        database="football_analytics",
    )

    engine = create_engine(connection_url)

    # 2. Получение сезонной статистики из SQL
    query = """
    SELECT
        team,
        SUM(goals) AS total_goals,
        SUM(shots) AS total_shots,
        SUM(shots_on_target) AS total_shots_on_target
    FROM team_match_stats
    GROUP BY team
    ORDER BY total_goals DESC;
    """

    try:
        with engine.connect() as connection:
            df = pd.read_sql_query(query, connection)
    finally:
        engine.dispose()

    if df.empty:
        raise ValueError("Запрос не вернул данные. Проверь таблицу team_match_stats.")

    # 3. Расчёт показателей
    df["shot_conversion_pct"] = (
        df["total_goals"] / df["total_shots"] * 100
    ).round(2)

    df["target_shot_pct"] = (
        df["total_shots_on_target"] / df["total_shots"] * 100
    ).round(2)

    df["goals_per_target_pct"] = (
        df["total_goals"] / df["total_shots_on_target"] * 100
    ).round(2)

    # 4. Вывод итоговой таблицы
    columns_to_show = [
        "team",
        "total_goals",
        "total_shots",
        "total_shots_on_target",
        "shot_conversion_pct",
        "target_shot_pct",
        "goals_per_target_pct",
    ]

    print("\n=== СЕЗОННАЯ СТАТИСТИКА КОМАНД АПЛ ===")
    print(df[columns_to_show].to_string(index=False))
    print(f"\nКоличество команд: {len(df)}")

    best_conversion = df.loc[df["shot_conversion_pct"].idxmax()]
    worst_conversion = df.loc[df["shot_conversion_pct"].idxmin()]

    print(
        f"\nЛучшая конверсия ударов: {best_conversion['team']} "
        f"({best_conversion['shot_conversion_pct']:.2f}%)"
    )
    print(
        f"Худшая конверсия ударов: {worst_conversion['team']} "
        f"({worst_conversion['shot_conversion_pct']:.2f}%)"
    )

    # 5. Сохранение таблицы
    csv_path = RESULTS_DIR / "team_analysis.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nТаблица сохранена: {csv_path}")

    # 6. График № 1: конверсия ударов в голы
    conversion_df = df.sort_values(
        "shot_conversion_pct",
        ascending=True,
    )

    fig, ax = plt.subplots(figsize=(12, 9))

    bars = ax.barh(
        conversion_df["team"],
        conversion_df["shot_conversion_pct"],
    )

    ax.bar_label(
        bars,
        fmt="%.2f%%",
        padding=5,
        fontsize=9,
    )

    ax.set_title(
        "АПЛ 2025/26: конверсия ударов в голы",
        fontsize=15,
        pad=15,
    )
    ax.set_xlabel("Голы / все удары, %", fontsize=11)
    ax.set_ylabel("Команда", fontsize=11)
    ax.set_xlim(0, conversion_df["shot_conversion_pct"].max() + 1.5)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)

    fig.tight_layout()
    conversion_path = RESULTS_DIR / "shot_conversion.png"
    fig.savefig(conversion_path, dpi=200, bbox_inches="tight")
    plt.show()
    plt.close(fig)

    # 7. График № 2: количество ударов и голов
    fig, ax = plt.subplots(figsize=(15, 10))

    ax.scatter(
        df["total_shots"],
        df["total_goals"],
        s=70,
    )

    for _, row in df.iterrows():
        ax.annotate(
            row["team"],
            xy=(row["total_shots"], row["total_goals"]),
            xytext=(8, 4),
            textcoords="offset points",
            fontsize=9,
            ha="left",
            va="bottom",
            annotation_clip=False,
        )

    ax.set_title(
        "АПЛ 2025/26: удары и забитые голы",
        fontsize=15,
        pad=15,
    )
    ax.set_xlabel("Количество ударов", fontsize=11)
    ax.set_ylabel("Количество голов", fontsize=11)

    ax.set_xlim(df["total_shots"].min() - 20, df["total_shots"].max() + 65)
    ax.set_ylim(df["total_goals"].min() - 4, df["total_goals"].max() + 5)

    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)

    fig.tight_layout()
    scatter_path = RESULTS_DIR / "shots_vs_goals.png"
    fig.savefig(scatter_path, dpi=200, bbox_inches="tight")
    plt.show()
    plt.close(fig)

    print("\nГрафики сохранены:")
    print(conversion_path)
    print(scatter_path)


if __name__ == "__main__":
    main()
