import re
import requests
import logging
from django.conf import settings

# setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Extract Spreadsheet ID
def extract_spreadsheet_id(google_sheet_link):
  """
    Extracts the spreadsheet ID from the Google Sheets URL.
    Raises a ValueError if the URL is invalid.
    """
  logger.info(f"Extracting spreadsheet ID from URL: {google_sheet_link}")
  match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', google_sheet_link)
  if match:
    spreadsheet_id = match.group(1)
    logger.debug(f"Spreadsheet ID extracted: {spreadsheet_id}")
    return spreadsheet_id
  else:
    logger.error("Invalid Google Sheets URL")
    raise ValueError("Invalid Google Sheets URL")

# Fetch Basic Google Sheet Data
def fetch_google_sheet_data(google_sheet_link):
  """
    Fetches basic data from a Google Sheet.
    """
  sheet_values = None

  try:
    spreadsheet_id = extract_spreadsheet_id(google_sheet_link)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchGet?ranges=Sheet1&key={settings.CREDENTIALS['GOOGLE_API_KEY']}"
    logger.info(f"Fetching data from URL: {url}")

    response = requests.get(url)
    response.raise_for_status()  # Raises an exception for 4xx/5xx responses

    data = response.json()
    sheet_values = data['valueRanges'][0].get('values', [])

    if len(sheet_values) == 0:
      logger.error(f"Empty Spreadsheet: {sheet_values}")
      raise Exception('Spreadsheet Is Empty')

    logger.debug(f"Data fetched: {sheet_values}")
    return sheet_values
  except requests.exceptions.RequestException as e:
    logger.error(f"Request failed: {e}")
    raise Exception(
      f"Spreadsheet Not Found, Make Sure It's Public Or Use Another Link"
    )
  except ValueError as ve:
    logger.error(f"Error extracting spreadsheet ID: {ve}")
    raise Exception(f"Your Spreadsheet ID Is Incorrect")
  except Exception as e:
    if sheet_values is not None and len(sheet_values) == 0:
      logger.error(f"Empty Spreadsheet: {sheet_values}")
      raise Exception('Spreadsheet Is Empty')

    logger.error(f"Unexpected error: {e}")
    raise Exception(f"Unexpected Error Happend, Please Try Again Later")

# Fetch data from Google Sheets API
def fetch_google_sheet_data_with_formatting(spreadsheet_id, api_key):
  url = (
    f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}'
    f'?fields=sheets.data.rowData.values.effectiveValue,sheets.data.rowData.values.textFormatRuns&key={api_key}'
  )

  try:
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
  except requests.exceptions.RequestException as e:
    logger.error("Failed to fetch data from Google Sheets API: %s", str(e))
    raise

# Parse text and formatting from a cell
def parse_cell_text_and_format(cell):
  try:
    formatted_text = cell.get('effectiveValue', {}).get('stringValue', '')
    text_format_runs = cell.get('textFormatRuns', [])
    return formatted_text, text_format_runs
  except Exception as e:
    logger.error("Failed to parse cell data: %s", str(e))
    raise

# Convert color data from Google's API format to RGB tuple
def extract_color_from_run(run):
  try:
    foreground_color = run.get('format', {}).get('foregroundColor', {})
    color_rgb = (
      int(foreground_color.get('red', 0) * 255),
      int(foreground_color.get('green', 0) * 255),
      int(foreground_color.get('blue', 0) * 255)
    )
    return color_rgb
  except Exception as e:
    logger.warning("Error extracting color data from run: %s", str(e))
    return (0, 0, 0)  # Default to black if no color is found

# Process each text format run
def process_text_format_runs(formatted_text, text_format_runs):
  word_data = []
  last_index = 0

  if not text_format_runs:
    words = formatted_text.split()
    for word in words:
      word_data.append(
        {
          'text': word,
          'color': (0, 0, 0)
        }
      )  # Default color: black
    return word_data

  for i, run in enumerate(text_format_runs):
    start_index = run.get('startIndex', 0)
    end_index = text_format_runs[i + 1]['startIndex'] if i + 1 < len(
      text_format_runs
    ) else len(formatted_text)

    # Add unformatted text before the current run
    if start_index > last_index:
      pre_run_text = formatted_text[last_index:start_index]
      pre_run_words = pre_run_text.split()
      for word in pre_run_words:
        word_data.append(
          {
            'text': word,
            'color': (0, 0, 0)
          }
        )  # Default color: black

    # Add formatted text for the current run
    run_text = formatted_text[start_index:end_index]
    run_words = run_text.split()
    color_rgb = extract_color_from_run(run)

    for word in run_words:
      word_data.append({'text': word, 'color': color_rgb})

    last_index = end_index

  # Add any trailing text after the last run
  if last_index < len(formatted_text):
    trailing_text = formatted_text[last_index:]
    trailing_words = trailing_text.split()
    for word in trailing_words:
      word_data.append(
        {
          'text': word,
          'color': (0, 0, 0)
        }
      )  # Default color: black

  return word_data

# Process a single row of data from Google Sheets
def process_row(row):
  row_data = []
  for cell in row.get('values', []):
    try:
      formatted_text, text_format_runs = parse_cell_text_and_format(cell)
      word_data = process_text_format_runs(formatted_text, text_format_runs)
      row_data.append(word_data)
    except Exception as e:
      logger.warning("Error processing row data: %s", str(e))
      row_data.append(None)  # Add None if there's an error in processing
  return row_data

# Main function to fetch and process word color data
def extract_word_color_data(google_sheet_link):
  try:
    # Extract the spreadsheet ID from the URL
    api_key = settings.CREDENTIALS['GOOGLE_API_KEY']
    spreadsheet_id = extract_spreadsheet_id(google_sheet_link)

    # Fetch data from Google Sheets API
    data = fetch_google_sheet_data_with_formatting(spreadsheet_id, api_key)
    rows = data['sheets'][0]['data'][0]['rowData']

    # Process each row
    sheet_data = []
    for row in rows:
      row_data = process_row(row)
      sheet_data.append(row_data)

    logger.info("Successfully fetched and processed word color data")
    return sheet_data

  except Exception as e:
    logger.error("Failed to fetch and process word color data: %s", str(e))
    return None
