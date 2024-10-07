# scripts/csv_combiner.py
import pandas as pd
import os
from config.scraper_config import SCRAPER_CONFIG, BASE_OUTPUT_DIR

def merge_csv_files():
    # Get the list of CSV files from the config
    csv_files = [config['output_file'] for config in SCRAPER_CONFIG.values()]

    # Initialize an empty list to hold DataFrames
    dfs = []

    # Read each CSV file into a DataFrame and append it to the list
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except FileNotFoundError:
            print(f"File not found: {file}")
        except pd.errors.EmptyDataError:
            print(f"File is empty: {file}")
        except pd.errors.ParserError:
            print(f"Error parsing file: {file}")

    # Concatenate all DataFrames into one
    merged_df = pd.concat(dfs, ignore_index=True)

    # Save the combined DataFrame to a new CSV file in the data folder
    output_file = os.path.join(BASE_OUTPUT_DIR, 'merge_csv_data.csv')
    merged_df.to_csv(output_file, index=False)

    print(f"All FAQ data has been successfully combined and saved to '{output_file}'")

if __name__ == "__main__":
    merge_csv_files()
