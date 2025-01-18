import pandas as pd
import os

def get_last_scraping_date(data_path):
    """
    Retrieves the last scraping date from the 'retrieval_date' column in a CSV file.

    Parameters:
        data_path (str): Path to the CSV file containing the scraping data.

    Returns:
        datetime or None: The latest retrieval_date if found, otherwise None.
    """
    try:
        # Load the data
        df = pd.read_csv(data_path, parse_dates=['retrieval_date'])

        # Check if the retrieval_date column exists
        if 'retrieval_date' not in df.columns:
            print("The 'retrieval_date' column is not present in the dataset.")
            return None

        # Find the most recent retrieval date
        last_date = df['retrieval_date'].max()

        if pd.isnull(last_date):
            print("No valid dates found in the 'retrieval_date' column.")
            return None

        return last_date
    except FileNotFoundError:
        print(f"File not found: {data_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def run_scraper():
    """
    Triggers the scraper script using the `os.system` command.
    """
    try:
        # Run the scraper script
        os.system("googlemaps-scraper/python scraper.py --N 100000")
        print("Scraping completed successfully!")
    except Exception as e:
        print(f"Error running the scraper: {e}")


def load_data(file_path, columns=None):
    """
    Load the CSV file into a DataFrame, selecting specific columns to optimize memory usage.

    Parameters:
        file_path (str): Path to the CSV file.
        columns (list, optional): List of column names to read. Defaults to None (reads all columns).

    Returns:
        pd.DataFrame: Loaded DataFrame or empty DataFrame on failure.
    """
    try:
        if columns:
            df = pd.read_csv(file_path, usecols=columns)
        else:
            df = pd.read_csv(file_path)  # Load all columns if none are specified
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

