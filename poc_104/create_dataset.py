# %%
from datasets import Dataset
import pandas as pd

# Load the data from the text files
pt_detected_fp_df = pd.read_csv("pt_detected_fp.txt")
pt_detected_fp_df = pt_detected_fp_df.rename(
    columns={"candidate_criteria_text": "text"}
)
pt_detected_fp_df

# %%

pt_tp_source_df = pd.read_csv("pt_tp_source.txt")
pt_tp_source_df = pt_tp_source_df.rename(columns={"source": "text"})

# %%
# Add a 'label' column to each DataFrame
pt_detected_fp_df["label"] = "LABEL_1"
pt_tp_source_df["label"] = "LABEL_0"

# Combine the dataframes
combined_df = pd.concat([pt_detected_fp_df, pt_tp_source_df], ignore_index=True)
combined_df = combined_df.drop(columns=["nct_id", "display_order", "name"])

# Create a Hugging Face Dataset
dataset = Dataset.from_pandas(combined_df)

# You can now work with the 'dataset' object, for example, print it
print(dataset)

# To save the dataset, you can use save_to_disk
dataset.to_csv("pt_inclusions.csv")
