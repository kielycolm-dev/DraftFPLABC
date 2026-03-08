from flask import Flask, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Load your CSV with Team, Gameweek, Points
df = pd.read_csv("FPL_draft_league_scores.csv")

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

    # Tiebreaker: look forward week by week
    while len(tied) > 1 and check_gw <= max_gw:

        next_week = df[(df["Gameweek"] == check_gw) & (df["Team"].isin(tied))]

        if next_week.empty:
            break

        next_max = next_week["Points"].max()
        tied = next_week[next_week["Points"] == next_max]["Team"].tolist()

        check_gw += 1

    # If tie still remains at end of season → split pot
    if len(tied) > 1:

        split = 50 / len(tied)

        for team in tied:
            money_tracker[team] += split
            weekly_wins[team] += 1

    else:

        winner = tied[0]

        money_tracker[winner] += 55
        weekly_wins[winner] += 1

    # Everyone pays $5
    for team in teams:
        money_tracker[team] -= 5




@app.route("/api/scores")
def api_scores():
    # Pivot the DataFrame: teams as rows, gameweeks as columns
    pivot = df.pivot(index="Team", columns="Gameweek", values="Points").fillna(0)

    # Add Total column
    pivot["Total"] = pivot.sum(axis=1)

    # Add Weekly wins and Net amount columns
    pivot["Weekly Wins"] = pivot.index.map(weekly_wins)
    pivot["Net $"] = pivot.index.map(money_tracker)

    # Sort by Total column
    pivot = pivot.sort_values("Total", ascending=False)

    pivot = pivot.sort_values("Total", ascending=False)

    # Prize distribution
    prizes = [350, 150, 100, 60]

    pivot["Position"] = range(1, len(pivot) + 1)
    pivot["Prize $"] = pivot["Position"].apply(lambda x: prizes[x-1] if x <= len(prizes) else 0)

    # Entry fee
    entry_fee = 60

    # Overall profit/loss
    pivot["Overall $"] = pivot["Net $"] + pivot["Prize $"] - entry_fee

# Convert to JSON for frontend
    return pivot.reset_index().to_json(orient="records")

@app.route("/")
def index():
    return render_template("index.html")

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
