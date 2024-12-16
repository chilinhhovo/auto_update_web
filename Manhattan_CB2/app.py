from flask import Flask, render_template, jsonify
import pandas as pd
import json
import openai
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()

# Access the OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask app
app = Flask(__name__)

# Define paths for Community Board CSVs
CSV_PATHS = {
    "manhattan-cb1": "Manhattan_CB1/Manhattan_CB1_with_content.csv",
    "manhattan-cb2": "Manhattan_CB2/Manhattan_CB2.csv",
    "manhattan-cb4": "Manhattan_CB4/Manhattan_CB4_with_content.csv",
    "bronx-cb1": "Bronx_CB1/Bronx_CB1_with_content.csv",
}

# Define community boards
community_boards = [
    {"name": "Manhattan Community Board 1", "link": "/manhattan-cb1"},
    {"name": "Manhattan Community Board 2", "link": "/manhattan-cb2"},
    {"name": "Manhattan Community Board 4", "link": "/manhattan-cb4"},
    {"name": "Bronx Community Board 1", "link": "/bronx-cb1"},
]


# Clean data and process for both ManCB1+ManCB4+BronxCB1
def clean_date(date):
    if isinstance(date, str):
        # Handle "YYYY Month YYYY" format (e.g., "2024 January 2024")
        if re.match(r"^\d{4}\s[A-Za-z]+\s\d{4}$", date):
            return pd.to_datetime(f"{date.split()[0]} {date.split()[1]} 1", errors="coerce")
        
        # Handle "Month YYYY Minutes" format (e.g., "January 2024 Minutes")
        if re.match(r"^[A-Za-z]+\s\d{4}\sMinutes$", date):
            month_year = " ".join(date.split()[:2])
            return pd.to_datetime(month_year, format="%B %Y", errors="coerce")
        
        # Handle "Month DD, YYYY Minutes" format (e.g., "June 20, 2024 Minutes")
        if re.match(r"^[A-Za-z]+\s\d{1,2},\s\d{4}\sMinutes$", date):
            # Extract the full date
            full_date = " ".join(date.split()[:3]).replace(",", "")
            return pd.to_datetime(full_date, format="%B %d %Y", errors="coerce")
    
    # Fallback: Try to parse standard date formats
    return pd.to_datetime(date, errors="coerce")




# Helper function to load and preprocess CSV
def load_and_process_data(csv_path):
    try:
        data = pd.read_csv(csv_path)
        data['Date'] = data['Date'].apply(clean_date)
        data = data.dropna(subset=['Date'])
        data['Year'] = data['Date'].dt.year
        data['Month_Num'] = data['Date'].dt.month
        data['Month_Name'] = data['Date'].dt.strftime('%B')
        return data
    except Exception as e:
        raise ValueError(f"Error loading or processing data from {csv_path}: {e}")


# Helper function for route logic (month content, summary, and votes)
def filter_data_and_render(board_id, year, month, template, process_fn=None):
    try:
        csv_path = CSV_PATHS.get(board_id)
        if not csv_path:
            return f"Invalid board ID: {board_id}", 404

        data = load_and_process_data(csv_path)

        # Filter rows for the specified year and month
        filtered_data = data[
            (data['Year'] == int(year)) & (data['Month_Name'].str.lower() == month.lower())
        ]

        # If a custom processing function is provided, use it
        content = process_fn(filtered_data) if process_fn else filtered_data['Content'].str.strip().tolist()

        # Render template
        return render_template(template, year=year, month=month, content_list=content)
    except Exception as e:
        return f"Error processing content for {board_id}: {e}"


@app.route("/")
def landing_page():
    return render_template("landing_page.html", community_boards=community_boards)


@app.route("/geojson")
def geojson():
    geojson_path = "/Users/chivo/Downloads/Foundations/HW/auto_update_web/Manhattan_CB2/static/Community Districts.geojson"
    try:
        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)
        return jsonify(geojson_data)
    except Exception as e:
        return jsonify({"error": f"Failed to load GeoJSON: {e}"}), 500


@app.route("/<board_id>")
def board_index(board_id):
    try:
        csv_path = CSV_PATHS.get(board_id)
        if not csv_path:
            return f"Invalid board ID: {board_id}", 404

        data = load_and_process_data(csv_path)
        sorted_data = data.sort_values(by=['Year', 'Month_Num'], ascending=[False, True])
        grouped_data = (
            sorted_data.groupby('Year', sort=False)
            .apply(lambda x: x[['Month_Name', 'Content']].to_dict(orient='records'))
            .to_dict()
        )

        # Dynamic template selection
        if board_id == "manhattan-cb1":
            template = "index_with_map.html"
        elif board_id == "manhattan-cb4":
            template = "CB4_index_with_map.html"
        elif board_id == "manhattan-cb2":
            template = "CB2_index_with_map.html"  # Use a new template for CB2 if required
        else:
            template = "bronx_index_with_map.html"

        return render_template(template, grouped_data=grouped_data, board_id=board_id)
    except Exception as e:
        return f"Error processing data for board {board_id}: {e}"



@app.route("/<board_id>/month/<year>/<month>")
def get_month_content(board_id, year, month):
    try:
        # Get the CSV file path from the mapping
        csv_path = CSV_PATHS.get(board_id)
        if not csv_path:
            return f"Invalid board ID: {board_id}", 404

        # Load and preprocess the data
        data = load_and_process_data(csv_path)

        # Filter rows for the specified year and month
        filtered_data = data[
            (data['Year'] == int(year)) & (data['Month_Name'].str.lower() == month.lower())
        ]

        # Extract content
        if not filtered_data.empty:
            content_list = filtered_data['Content'].str.strip().tolist()

            # Filter out only the bottom half of the content
            filtered_content = []
            for content in content_list:
                if "Back to Previous Page" in content:
                    # Split at "Back to Previous Page" and take the bottom half
                    parts = content.split("Back to Previous Page")
                    filtered_content.append(parts[-1].strip())  # Get content after the marker
                else:
                    filtered_content.append(content)  # Fallback if marker not found
        else:
            filtered_content = ["No content available."]

        return render_template("month_content.html", year=year, month=month, content_list=filtered_content)

    except Exception as e:
        return f"Error processing month content for board {board_id}: {e}"


@app.route("/summary/<year>/<month>")
@app.route("/<board_id>/summary/<year>/<month>")
def get_summary(board_id="manhattan-cb1", year=None, month=None):
    def summarize(filtered_data):
        full_content = " ".join(filtered_data['Content'].tolist()) if not filtered_data.empty else "No content available."
        if not full_content.strip() or full_content == "No content available.":
            return "No summary available."

        try:
            # Call OpenAI API for summary
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Summarize the meeting minutes."},
                    {"role": "user", "content": f"Summarize: {full_content[:4000]}"},
                ],
            )
            return response.choices[0].message['content']
        except Exception as e:
            return f"Error generating summary: {e}"

    try:
        # Validate board_id and fetch CSV path
        if board_id not in CSV_PATHS:
            return f"Invalid board ID: {board_id}", 404
        csv_path = CSV_PATHS[board_id]

        # Load and filter data
        data = load_and_process_data(csv_path)
        filtered_data = data[
            (data['Year'] == int(year)) & (data['Month_Name'].str.lower() == month.lower())
        ]

        # Generate summary
        summary = summarize(filtered_data)

        # Render template with summary
        return render_template("summary.html", year=year, month=month, summary=summary)
    except Exception as e:
        return f"Error processing summary: {e}"



@app.route("/vote/<year>/<month>")
@app.route("/<board_id>/vote/<year>/<month>")
def get_vote_summary(board_id=None, year=None, month=None):
    # Set default board_id if not provided
    if board_id is None:
        board_id = "manhattan-cb1"

    def extract_votes(filtered_data):
        full_content = " ".join(filtered_data['Content'].tolist()) if not filtered_data.empty else ""
        if not full_content:
            return ["No voting decisions available."]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Extract voting decisions from the meeting minutes."},
                    {"role": "user", "content": f"Extract votes: {full_content[:4000]}"},
                ],
            )
            return [line.strip() for line in response.choices[0].message['content'].split("\n") if line.strip()]
        except Exception as e:
            return [f"Error extracting votes: {e}"]

    try:
        # Validate board_id and process the request
        if board_id not in CSV_PATHS:
            return f"Invalid board ID: {board_id}", 404
        
        # Call helper function to load, filter, and render data
        return filter_data_and_render(board_id, year, month, "vote.html", extract_votes)

    except Exception as e:
        return f"Error processing vote summary: {e}"



@app.route("/month/<year>/<month>")
def default_month_content(year, month):
    # Default to Manhattan CB1
    return get_month_content("manhattan-cb1", year, month)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
