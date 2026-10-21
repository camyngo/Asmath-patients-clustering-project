# Rena Ahn
# read_files.py (Python)
# 4 November 2024
# Reads patient files (.xlsx) and converts them to .csv files

import numpy as np
import pandas as pd
import os

# Constant Variables
MIN_NUM_VALUES = 200

# 114_medinfo file -> DataFrame
demographic_df = pd.DataFrame(pd.read_excel('data_org/Demographic.xlsx'))

# new UID values
new_uid = np.where(demographic_df['UID2'].isna(), demographic_df['UID1'], demographic_df['UID2'])
demographic_df['UID'] = pd.Series(new_uid)
demographic_df = demographic_df.drop(['UID1', 'UID2'], axis=1)

# listed patient id
patient_ids = list(demographic_df['ID'])

# individual patient files -> DataFrame
folder_path = 'data_org/SCH_asthma_114'
patient_dfs = {}

for filename in os.listdir(folder_path):
    # converting patient file -> Dataframe
    file_path = folder_path + '/' + filename
    patient_df = pd.DataFrame(pd.read_excel(file_path))

    patient_id = patient_df.iloc[2, 0] if patient_df.iloc[1, 0][0] == 'A' \
                                       else patient_df.iloc[1, 0]
    if patient_id in patient_ids:
        # new dataframe 
        new_df = pd.DataFrame()
        new_df['date'] = patient_df.iloc[2:, 1]

        # add columns if missing values are less than the minimum threshold
        num_values = patient_df.shape[0]
        min_threshold = num_values - MIN_NUM_VALUES
           #guarantees at least 200 values are provided
        if patient_df.iloc[2:, 6].isna().sum() < min_threshold:
            new_df['pefr_am'] = patient_df.iloc[2:, 6]
        if patient_df.iloc[2:, 7].isna().sum() < min_threshold:
            new_df['pefr_pm'] = patient_df.iloc[2:, 7]
        if patient_df.iloc[2:, 8].isna().sum() < min_threshold:
            new_df['pefr_other'] = patient_df.iloc[2:, 8]

        if new_df.shape[1] > 1:   #ensures there is PEFR data
            patient_dfs[patient_id] = new_df

# checking patients removed and ensuring counts match
new_patient_ids = list(patient_dfs.keys())
patients_removed = len(patient_ids) - len(new_patient_ids)

valid_rows = demographic_df['ID'].isin(new_patient_ids)
removed_df = demographic_df[~valid_rows]

print('Number of Patients Removed: ', patients_removed)
print('Number of Patients Found with Removed Ids: ', removed_df.shape[0])

# updating patient id list and demographic DataFrame
patient_ids = new_patient_ids
demographic_df = demographic_df[valid_rows]

# storing dataframes -> csv files to data_read folder
demographic_df.to_csv('data_read/demographic_all.csv')

demographic_df_part = demographic_df.drop(['BCODE', 'UID'], axis=1)
demographic_df_part.to_csv('data_read/demographic.csv')

for name, df in patient_dfs.items():
    new_file_path = 'data_read/patients/' + name
    df.to_csv(new_file_path)
