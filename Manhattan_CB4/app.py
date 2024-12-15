from flask import Flask, render_template, jsonify
import pandas as pd
import json
import openai
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Access the OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask app
app = Flask(__name__)

# Load the CSV data
csv_path = "/Users/chivo/Downloads/Foundations/HW/auto_update_web/Manhattan_CB4/Manhattan_CB4_with_content.csv"
try:
    data = pd.read_csv(csv_path)
except Exception as e:
    raise ValueError(f"Error loading CSV file: {e}")

# Ensure 'Date' column exists
if "Date" not in data.columns:
    raise ValueError("CSV file must contain a 'Date' column.")

@app.route("/")
def index():
    # Create a local copy of the global data
    local_data = data.copy()

    # Sort by 'Date' column (if applicable)
    local_data = local_data.sort_values(by=['Date'], ascending=False)

    # Extract Year from 'Date'
    local_data['Year'] = pd.to_datetime(local_data['Date'], errors='coerce').dt.year

    # Group by Year
    grouped_data = (
        local_data.groupby('Year', sort=False)
        .apply(lambda x: x[['Date', 'Content']].to_dict(orient='records'))
        .to_dict()
    )

    return render_template("index_with_map.html", grouped_data=grouped_data)

@app.route("/geojson")
def geojson():
    geojson_path = "/Users/chivo/Downloads/Foundations/HW/auto_update_web/Manhattan_CB4/static/Community Districts.geojson"
    try:
        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)
        return jsonify(geojson_data)
    except Exception as e:
        return jsonify({"error": f"Failed to load GeoJSON: {e}"}), 500

@app.route("/month/<year>/<month>")
def get_month_content(year, month):
    # Filter data by the given year and month
    local_data = data.copy()
    local_data['Year'] = pd.to_datetime(local_data['Date'], errors='coerce').dt.year
    local_data['Month_Name'] = pd.to_datetime(local_data['Date'], errors='coerce').dt.strftime('%B')

    # Filter rows for the specified year and month
    filtered_data = local_data[
        (local_data['Year'] == int(year)) & (local_data['Month_Name'].str.lower() == month.lower())
    ]

    # Extract the content
    if not filtered_data.empty:
        content_list = filtered_data['Content'].tolist()
    else:
        content_list = ["No content available for this month."]

    return render_template("month_content.html", year=year, month=month, content_list=content_list)

@app.route("/summary/<year>/<month>")
def get_summary(year, month):
    # Filter data by the given year and month
    local_data = data.copy()
    local_data['Year'] = pd.to_datetime(local_data['Date'], errors='coerce').dt.year
    local_data['Month_Name'] = pd.to_datetime(local_data['Date'], errors='coerce').dt.strftime('%B')

    # Filter rows for the specified year and month
    filtered_data = local_data[
        (local_data['Year'] == int(year)) & (local_data['Month_Name'].str.lower() == month.lower())
    ]

    # Extract the content
    if not filtered_data.empty:
        content_list = filtered_data['Content'].tolist()
        full_content = " ".join(content_list)
    else:
        return render_template(
            "summary.html", year=year, month=month, summary="No content available for this month."
        )

    # Generate a summary using OpenAI
    summary = "No summary available."
    if full_content:
        try:
            truncated_content = full_content[:4000]  # Truncate to fit GPT's input limit
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes meeting transcripts into concise summaries.",
                    },
                    {
                        "role": "user",
                        "content": f"Summarize the following meeting minutes: {truncated_content}",
                    },
                ],
            )
            summary = response.choices[0].message['content']
        except Exception as e:
            summary = f"Error generating summary: {str(e)}"

    return render_template("summary.html", year=year, month=month, summary=summary)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
