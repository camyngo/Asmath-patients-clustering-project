# Improved read_files.py with grouping by completeness threshold
import numpy as np
import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
FOLDER_PATH = 'data_org/SCH_asthma_114'
OUTPUT_FOLDER = 'data_read/patients_by_completeness'
DEMOGRAPHIC_PATH = 'data_org/Demographic.xlsx'
HIGH_THRESHOLD = 0.8  # 80% completeness
MEDIUM_THRESHOLD = 0.5  # 50% completeness

# Create output directories for different completeness levels
high_completeness_folder = os.path.join(OUTPUT_FOLDER, 'high_completeness')
medium_completeness_folder = os.path.join(OUTPUT_FOLDER, 'medium_completeness')
low_completeness_folder = os.path.join(OUTPUT_FOLDER, 'low_completeness')
os.makedirs(high_completeness_folder, exist_ok=True)
os.makedirs(medium_completeness_folder, exist_ok=True)
os.makedirs(low_completeness_folder, exist_ok=True)

# Load demographic data
demographic_df = pd.read_excel(DEMOGRAPHIC_PATH)
new_uid = np.where(demographic_df['UID2'].isna(), demographic_df['UID1'], demographic_df['UID2'])
demographic_df['UID'] = pd.Series(new_uid)
demographic_df = demographic_df.drop(['UID1', 'UID2'], axis=1)
patient_ids = list(demographic_df['ID'])

# Prepare dictionary to hold processed data
patient_dfs = {}

# Process each patient file in the folder
for filename in os.listdir(FOLDER_PATH):
    file_path = os.path.join(FOLDER_PATH, filename)
    try:
        # Load patient file
        patient_df = pd.read_excel(file_path)

        # Extract patient ID
        patient_id = patient_df.iloc[2, 0] if 'A' in str(patient_df.iloc[1, 0]) else patient_df.iloc[1, 0]

        if patient_id in patient_ids:
            new_df = pd.DataFrame()
            new_df['date'] = patient_df.iloc[2:, 1]

            # Check completeness for each PEFR column and calculate overall completeness
            total_rows = patient_df.shape[0] - 2  # Exclude header rows
            pefr_columns = ['pefr_am', 'pefr_pm', 'pefr_other']
            completeness = {}

            # Calculate completeness percentage for each PEFR column
            for col, name in zip([6, 7, 8], pefr_columns):
                completeness[name] = patient_df.iloc[2:, col].notna().sum() / total_rows

            # Calculate average completeness across PEFR columns
            avg_completeness = np.mean(list(completeness.values()))

            # Determine folder based on completeness
            if avg_completeness >= HIGH_THRESHOLD:
                target_folder = high_completeness_folder
            elif avg_completeness >= MEDIUM_THRESHOLD:
                target_folder = medium_completeness_folder
            else:
                target_folder = low_completeness_folder

            # Add columns to the new DataFrame (allow incomplete columns)
            new_df['pefr_am'] = patient_df.iloc[2:, 6]
            new_df['pefr_pm'] = patient_df.iloc[2:, 7]
            new_df['pefr_other'] = patient_df.iloc[2:, 8]

            # Store the DataFrame for each patient in the appropriate folder
            patient_dfs[patient_id] = new_df
            output_path = os.path.join(target_folder, f"{patient_id}.csv")
            new_df.to_csv(output_path, index=False)
            logging.info(f"Saved data for patient {patient_id} in {target_folder} (completeness: {avg_completeness:.2%})")

    except Exception as e:
        logging.error(f"Error processing file {filename}: {e}")

# Check and filter demographic data based on valid patient IDs
valid_patient_ids = list(patient_dfs.keys())
patients_removed = len(patient_ids) - len(valid_patient_ids)
logging.info(f"Number of patients excluded due to unmatched IDs: {patients_removed}")

valid_rows = demographic_df['ID'].isin(valid_patient_ids)
demographic_df = demographic_df[valid_rows]

# Save demographic data
demographic_output_folder = 'data_read'
os.makedirs(demographic_output_folder, exist_ok=True)
demographic_df.to_csv(os.path.join(demographic_output_folder, 'demographic_all.csv'), index=False)
demographic_df.drop(['BCODE', 'UID'], axis=1).to_csv(os.path.join(demographic_output_folder, 'demographic.csv'), index=False)

logging.info("Data processing completed successfully, with patients grouped by completeness levels.")