from flask import Flask, jsonify, render_template
import requests
import pandas as pd
import time
import os

app = Flask(__name__)

LEAGUE_ID = 2545
BASE_URL = "https://draft.premierleague.com/api"

CACHE = {
    "data": None,
    "last_updated": 0
}

CACHE_REFRESH = 3600  # seconds (1 hour)


def load_fpl_data():

    current_time = time.time()

    # Return cached data if it's still fresh
    if CACHE["data"] is not None and (current_time - CACHE["last_updated"]) < CACHE_REFRESH:
        return CACHE["data"]

    league_url = f"{BASE_URL}/league/{LEAGUE_ID}/details"
    league_data = requests.get(league_url, timeout=10).json()

    teams = league_data["league_entries"]

    all_scores = []

    for team in teams:
        entry_id = team["entry_id"]
        team_name = team["entry_name"]

        history_url = f"{BASE_URL}/entry/{entry_id}/history"
        history_data = requests.get(history_url, timeout=10).json()

        for gw in history_data["history"]:
            all_scores.append({
                "Team": team_name,
                "Gameweek": gw["event"],
                "Points": gw["points"],
                "Total Points": gw["total_points"]
            })

        time.sleep(0.2)

    df = pd.DataFrame(all_scores)
    df = df.sort_values(["Gameweek", "Team"])

    CACHE["data"] = df
    CACHE["last_updated"] = current_time

    return df


@app.route("/api/scores")
def api_scores():

    df = load_fpl_data()

    gameweeks = sorted(df["Gameweek"].unique())
    teams = df["Team"].unique()

    money_tracker = {team: 0 for team in teams}
    weekly_wins = {team: 0 for team in teams}

    max_gw = max(gameweeks)

    for gw in gameweeks:

        week_df = df[df["Gameweek"] == gw]

        max_score = week_df["Points"].max()
        tied = week_df[week_df["Points"] == max_score]["Team"].tolist()

        check_gw = gw + 1

        while len(tied) > 1 and check_gw <= max_gw:

            next_week = df[(df["Gameweek"] == check_gw) & (df["Team"].isin(tied))]

            if next_week.empty:
                break

            next_max = next_week["Points"].max()
            tied = next_week[next_week["Points"] == next_max]["Team"].tolist()

            check_gw += 1

        if len(tied) > 1:

            split = 55 / len(tied)

            for team in tied:
                money_tracker[team] += split
                weekly_wins[team] += 1

        else:

            winner = tied[0]

            money_tracker[winner] += 55
            weekly_wins[winner] += 1

        for team in teams:
            money_tracker[team] -= 5

    pivot = df.pivot(index="Team", columns="Gameweek", values="Points").fillna(0)

    # Convert column names to strings so JSON serialization works
    pivot.columns = pivot.columns.astype(str)

    pivot["Total"] = pivot.sum(axis=1)


    pivot["Weekly Wins"] = pivot.index.map(weekly_wins)
    pivot["Net $"] = pivot.index.map(money_tracker)

    pivot = pivot.sort_values("Total", ascending=False)

    prizes = [350, 150, 100, 60]

    pivot["Position"] = range(1, len(pivot) + 1)
    pivot["Prize $"] = pivot["Position"].apply(lambda x: prizes[x-1] if x <= len(prizes) else 0)

    entry_fee = 60
    pivot["Overall $"] = pivot["Net $"] + pivot["Prize $"] - entry_fee

    return jsonify(pivot.reset_index().to_dict(orient="records"))


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
