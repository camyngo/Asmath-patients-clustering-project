import pandas as pd
from pathlib import Path

# Define the root directory for the imputed data
IMPUTED_FOLDER = Path("data_read/imputed_data")  # Replace with the actual path to `imputed_data`
output_file = "Consolidated_Patient_PEFR_Statistics.xlsx"

# List to accumulate all patient statistics
all_patient_stats = []

# Loop through each CSV file in the imputed folder and all subdirectories
for file_path in IMPUTED_FOLDER.rglob("*.csv"):  # Use rglob to search recursively
    print(f"Processing file: {file_path}")  # Debug: Print each file path being processed

    # Extract patient ID from the filename
    patient_id = file_path.stem.split("_")[-1]

    try:
        # Load the patient data
        df = pd.read_csv(file_path)

        # Check if the dataframe is loaded and columns are present
        if df.empty:
            print(f"File {file_path} is empty.")
            continue

        # Initialize a dictionary to store statistics for this patient
        patient_summary = {'patient_id': patient_id}

        # Calculate statistics for each PEFR column and add them to the dictionary
        for column in ['pefr_am', 'pefr_pm', 'pefr_other']:
            if column in df.columns and not df[column].isna().all():  # Ensure the column exists and has data
                patient_summary.update({
                    f'{column}_count': df[column].count(),
                    f'{column}_min': df[column].min(skipna=True),
                    f'{column}_median': df[column].median(skipna=True),
                    f'{column}_max': df[column].max(skipna=True),
                    f'{column}_mean': df[column].mean(skipna=True),
                    f'{column}_sum': df[column].sum(skipna=True),
                    f'{column}_std': df[column].std(skipna=True),
                    f'{column}_skew': df[column].skew(skipna=True)
                })
            else:
                print(f"Column {column} missing or has only NaN values in file {file_path}.")
                # If column is missing or has NaN values, populate with NaNs for consistency
                patient_summary.update({
                    f'{column}_count': None,
                    f'{column}_min': None,
                    f'{column}_median': None,
                    f'{column}_max': None,
                    f'{column}_mean': None,
                    f'{column}_sum': None,
                    f'{column}_std': None,
                    f'{column}_skew': None
                })

        # Append the patient's summary to the list
        all_patient_stats.append(patient_summary)

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

# Create a DataFrame from the list of all patient summaries
consolidated_df = pd.DataFrame(all_patient_stats)

# Write the consolidated DataFrame to an Excel file
with pd.ExcelWriter(output_file) as writer:
    consolidated_df.to_excel(writer, sheet_name="Patient_PEFR_Statistics", index=False)

print(f"Consolidated statistics summary saved to {output_file}")