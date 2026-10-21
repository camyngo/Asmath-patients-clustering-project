import pandas as pd
import os

# Define the base folder where patient data is stored
BASE_FOLDER = "data_read/cleaned_patients_by_yearly_data"
CLEANED_FOLDER = "data_read/cleaned_patients"  # New folder for processed files

# Create the cleaned folder if it does not exist
os.makedirs(CLEANED_FOLDER, exist_ok=True)

# Loop through each completeness level folder
for completeness_level in ['high_completeness', 'medium_completeness', 'low_completeness']:
    folder_path = os.path.join(BASE_FOLDER, completeness_level)
    cleaned_folder_path = os.path.join(CLEANED_FOLDER, completeness_level)
    os.makedirs(cleaned_folder_path, exist_ok=True)

    # Ensure the folder exists
    if not os.path.exists(folder_path):
        print(f"Skipping {completeness_level}: folder not found.")
        continue

    # Process each CSV file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)

            # Read the patient data
            patient_df = pd.read_csv(file_path)

            # Define the PEFR columns to check
            columns_to_check = ['pefr_am', 'pefr_pm', 'pefr_other']

            # Step 1: Drop rows where all PEFR columns are NaN
            patient_df = patient_df.dropna(subset=columns_to_check, how='all')

            # Step 2: For remaining rows, fill NaNs in PEFR columns with "Na"
            # Convert columns to string type before filling
            patient_df[columns_to_check] = patient_df[columns_to_check].astype(str).replace("nan", "NA")

            # Step 3: Drop rows where all PEFR values are "0" (casted to string for consistency)
            patient_df = patient_df[~(patient_df[columns_to_check] == "0").all(axis=1)]

            # Step 4: Verify there are no NaN values remaining in the specified columns
            remaining_nans = patient_df[columns_to_check].isnull().any()
            if remaining_nans.any():
                nan_columns = [column for column, has_nan in remaining_nans.items() if has_nan]
                print(f"Warning: {filename} still contains NaN values in columns: {nan_columns}")
            else:
                print(f"No NaN values left in {filename}. Data is fully cleaned.")

            # Save the cleaned DataFrame to the new folder
            cleaned_file_path = os.path.join(cleaned_folder_path, f"cleaned_{filename}")
            patient_df.to_csv(cleaned_file_path, index=False)
            print(f"Saved cleaned data for {filename} to {cleaned_file_path}")