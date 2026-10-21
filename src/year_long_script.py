import numpy as np
import pandas as pd
import os
import logging
from datetime import timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Paths
OUTPUT_FOLDER = 'data_read/patients_by_completeness'
CLEANED_OUTPUT_FOLDER = 'data_read/cleaned_patients_by_yearly_data'

# Create output directories for each completeness level in the cleaned folder
for completeness_level in ['high_completeness', 'low_completeness', 'medium_completeness']:
    os.makedirs(os.path.join(CLEANED_OUTPUT_FOLDER, completeness_level), exist_ok=True)

def has_continuous_year_or_12_months(dates):
    # Convert dates to datetime with flexible parsing, allowing mixed formats
    parsed_dates = pd.to_datetime(dates, errors='coerce')
    sorted_dates = sorted(parsed_dates.dropna().unique())  # Remove NaT values after parsing

    # Check for a continuous year (365 days)
    for i in range(len(sorted_dates)):
        if sorted_dates[i] + timedelta(days=365) <= sorted_dates[-1]:
            return True

    # Check for 12 consecutive months
    months_seen = {sorted_dates[0].month}  # Initialize with the first month
    for i in range(1, len(sorted_dates)):
        # Track month sequence
        if sorted_dates[i].month != sorted_dates[i - 1].month:
            months_seen.add(sorted_dates[i].month)
        # If 12 unique months are found, it's considered a full year
        if len(months_seen) == 12:
            return True
    return False

# Process each patient in each completeness level folder
for completeness_level in ['high_completeness', 'medium_completeness', 'low_completeness']:
    folder_path = os.path.join(OUTPUT_FOLDER, completeness_level)

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        try:
            # Load patient data
            patient_df = pd.read_csv(file_path)

            # Step 1: Check if data spans at least one year continuously
            if not has_continuous_year_or_12_months(patient_df['date']):
                logging.info(f"Skipping {filename} - does not have 1 year of continuous data.")
                continue

            # Step 2: Ensure at least one PEFR column has values for each date
            patient_df['has_pefr'] = patient_df[['pefr_am', 'pefr_pm', 'pefr_other']].notna().any(axis=1)
            patient_df = patient_df[patient_df['has_pefr']].drop(columns=['has_pefr'])

            # Step 3: Remove dates that have no PEFR values in any column
            cleaned_df = patient_df.dropna(subset=['pefr_am', 'pefr_pm', 'pefr_other'], how='all')

            # Save the cleaned data if it still has data after filtering
            if not cleaned_df.empty:
                output_path = os.path.join(CLEANED_OUTPUT_FOLDER, completeness_level, filename)
                cleaned_df.to_csv(output_path, index=False)
                logging.info(f"Saved cleaned data for {filename} in {completeness_level}.")
            else:
                logging.info(f"Skipping {filename} - no data left after cleaning.")

        except Exception as e:
            logging.error(f"Error processing file {filename} in {completeness_level}: {e}")

logging.info("Data processing and cleaning completed.")
