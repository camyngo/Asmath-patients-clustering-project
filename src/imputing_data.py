import pandas as pd
import os

# Define base and output folders
CLEANED_FOLDER = "data_read/cleaned_patients"
IMPUTED_FOLDER = "data_read/imputed_data"

os.makedirs(IMPUTED_FOLDER, exist_ok=True)

# Loop through completeness level folders
for completeness_level in ['high_completeness', 'medium_completeness', 'low_completeness']:
    folder_path = os.path.join(CLEANED_FOLDER, completeness_level)
    imputed_folder_path = os.path.join(IMPUTED_FOLDER, completeness_level)
    os.makedirs(imputed_folder_path, exist_ok=True)

    if not os.path.exists(folder_path):
        print(f"Skipping {completeness_level}: folder not found.")
        continue

    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)
            patient_df = pd.read_csv(file_path)

            columns_to_check = ['pefr_am', 'pefr_pm', 'pefr_other']

            # Step 1: Identify outliers and mark as missing with `pd.NA`
            for column in columns_to_check:
                patient_df[column] = pd.to_numeric(patient_df[column], errors='coerce')
                patient_df.loc[patient_df[column] > 1000, column] = pd.NA

            # Step 2: Perform filling logic for missing values if missing data is <50%
            for column in columns_to_check:
                missing_count = patient_df[column].isna().sum()
                total_count = len(patient_df[column])

                # Check if missing data is less than 50%
                if missing_count / total_count < 0.5:
                    na_indices = patient_df[patient_df[column].isna()].index
                    gap_start = None

                    for i in range(len(na_indices)):
                        if i == 0 or na_indices[i] != na_indices[i - 1] + 1:
                            gap_start = na_indices[i]

                        if i == len(na_indices) - 1 or na_indices[i] + 1 != na_indices[i + 1]:
                            gap_end = na_indices[i]
                            gap_length = gap_end - gap_start + 1

                            # Apply forward fill for gaps of 7 or fewer rows
                            if gap_length <= 7:
                                patient_df.loc[gap_start:gap_end, column] = patient_df[column].ffill().loc[gap_start:gap_end]
                            # Apply linear interpolation for gaps of 14 or more rows
                            elif gap_length >= 14:
                                patient_df.loc[gap_start:gap_end, column] = patient_df[column].interpolate(method='linear').loc[gap_start:gap_end]

                    print(f"Performed filling for {column} in {filename}")
                else:
                    print(f"Skipped filling for {column} in {filename} due to >50% missing data")

            # Step 3: Convert NaNs to "NA" when saving the final output
            patient_df[columns_to_check] = patient_df[columns_to_check].fillna("NA")

            # Save the cleaned DataFrame to the new folder
            imputed_file_path = os.path.join(imputed_folder_path, f"imputed_{filename}")
            patient_df.to_csv(imputed_file_path, index=False)
            print(f"Saved imputed data for {filename} to {imputed_file_path}")