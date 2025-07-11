import pandas as pd


src = "data/20250506_GBIF_species/20250506_GBIF_species.csv"

data = pd.read_csv(src, sep='\t')
print(data.head())

# Basic shape of the data
print("\nShape of the dataset (rows, columns):", data.shape)

# Column names and data types
print("\nColumn names and data types:")
print(data.dtypes)

# Summary statistics for numeric columns
print("\nSummary statistics for numeric columns:")
print(data.describe())

# Summary statistics for object (categorical) columns
print("\nSummary statistics for categorical columns:")
print(data.describe(include=['object']))

# Check for missing values
print("\nMissing values per column:")
print(data.isnull().sum())

# Check for duplicated rows
print("\nNumber of duplicated rows:", data.duplicated().sum())

# Show unique values for each column (optional but useful for categorical data)
print("\nNumber of unique values per column:")
print(data.nunique())

first_row = data.iloc[0]
print("\n---\nFirst row contents:")
for col, val in first_row.items():
    print(f"{col}: {val}")
