from flask import Flask, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Load your CSV with Team, Gameweek, Points
df = pd.read_csv("FPL_draft_league_scores.csv")

@app.route("/api/scores")
def api_scores():
    # Pivot the DataFrame: teams as rows, gameweeks as columns
    pivot = df.pivot(index="Team", columns="Gameweek", values="Points").fillna(0)

    # Add Total column
    pivot["Total"] = pivot.sum(axis=1)

    # Convert to JSON for frontend
    return pivot.reset_index().to_json(orient="records")

@app.route("/")
def index():
    return render_template("index.html")

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
