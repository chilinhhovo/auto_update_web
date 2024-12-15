# #Debugging, py failed since I moved folder 
# from flask import Flask

# # Initialize Flask app
# app = Flask(__name__)

# @app.route("/")
# def index():
#     return "Flask is running!"

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5001, debug=True)

from flask import Flask, render_template, jsonify, request
import pandas as pd
import json
import openai
import re
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Access the OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

#Turned out I was missing this
app = Flask(__name__)

# Load the CSV data
csv_path = "Manhattan_CB1/Manhattan_CB1.csv"
try:
    data = pd.read_csv(csv_path)
except Exception as e:
    raise ValueError(f"Error loading CSV file: {e}")

# Ensure 'Date' column exists
if "Date" not in data.columns:
    raise ValueError("CSV file must contain a 'Date' column.")

# Function to clean and standardize date formats
def clean_date_column(date_series):
    cleaned_dates = []
    for date in date_series:
        if isinstance(date, str):
            # Match formats like "2024 January 2024"
            match = re.match(r"^(\d{4})\s([A-Za-z]+)\s\d{4}$", date)
            if match:
                cleaned_date = f"{match.group(1)} {match.group(2)} 1"  # Set day to 1 for consistency
                cleaned_dates.append(cleaned_date)
            else:
                # Keep the original date for other formats
                cleaned_dates.append(date)
        else:
            cleaned_dates.append(date)  # Non-string values (e.g., NaN) remain unchanged
    return pd.Series(cleaned_dates)

@app.route("/")
def index():
    # Create a local copy of the global data
    local_data = data.copy()

    # Clean the Date column to handle mixed formats
    local_data['Date'] = clean_date_column(local_data['Date'])

    # Parse 'Date' column to ensure proper handling
    local_data['Date'] = pd.to_datetime(local_data['Date'], errors='coerce')

    # Drop rows with invalid or missing dates
    local_data = local_data.dropna(subset=['Date'])

    # Extract Year and Month
    local_data['Year'] = local_data['Date'].dt.year
    local_data['Month_Num'] = local_data['Date'].dt.month
    local_data['Month_Name'] = local_data['Date'].dt.strftime('%B')

    # Sort by Year (descending) and Month (ascending)
    sorted_data = local_data.sort_values(by=['Year', 'Month_Num'], ascending=[False, True])

    # Group by Year
    grouped_data = (
        sorted_data.groupby('Year', sort=False)
        .apply(lambda x: x[['Month_Name', 'Content']].to_dict(orient='records'))
        .to_dict()
    )

    return render_template("index_with_map.html", grouped_data=grouped_data)



@app.route("/geojson")
def geojson():
    geojson_path = "static/Community Districts.geojson"
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
    local_data['Date'] = clean_date_column(local_data['Date'])
    local_data['Date'] = pd.to_datetime(local_data['Date'], errors='coerce')
    local_data['Year'] = local_data['Date'].dt.year
    local_data['Month_Name'] = local_data['Date'].dt.strftime('%B')

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
    local_data['Date'] = clean_date_column(local_data['Date'])
    local_data['Date'] = pd.to_datetime(local_data['Date'], errors='coerce')
    local_data['Year'] = local_data['Date'].dt.year
    local_data['Month_Name'] = local_data['Date'].dt.strftime('%B')

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
            # Ensure the text is short enough for OpenAI
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

@app.route("/vote/<year>/<month>")
def get_vote_summary(year, month):
    # Filter data by the given year and month
    local_data = data.copy()
    local_data['Date'] = pd.to_datetime(local_data['Date'], errors='coerce')
    local_data['Year'] = local_data['Date'].dt.year
    local_data['Month_Name'] = local_data['Date'].dt.strftime('%B')

    # Filter rows for the specified year and month
    filtered_data = local_data[
        (local_data['Year'] == int(year)) & (local_data['Month_Name'].str.lower() == month.lower())
    ]

    # Extract content
    if not filtered_data.empty:
        content_list = filtered_data['Content'].tolist()
        full_content = " ".join(content_list)
    else:
        return render_template("vote.html", year=year, month=month, vote_list=[])

    # Process the content to extract voting decisions
    vote_list = []  # Default to an empty list if nothing is found
    if full_content.strip():  # Ensure there's meaningful content
        try:
            # Ensure the text is short enough for OpenAI
            truncated_content = full_content[:4000]  # Truncate to fit GPT's input limit
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts voting decisions from meeting transcripts.",
                    },
                    {
                        "role": "user",
                        "content": f"Please extract voting decisions from the following meeting minutes:\n\n{truncated_content}",
                    },
                ],
            )
            vote_list_raw = response.choices[0].message['content']
            vote_list = [vote.strip() for vote in vote_list_raw.split("\n") if vote.strip()]
        except Exception as e:
            vote_list = [f"Error processing votes: {str(e)}"]

    return render_template("vote.html", year=year, month=month, vote_list=vote_list)






    # Extract the content
    if not filtered_data.empty:
        content_list = filtered_data['Content'].tolist()
    else:
        content_list = ["No content available for this month."]

    return render_template("month_content.html", year=year, month=month, content_list=content_list)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
