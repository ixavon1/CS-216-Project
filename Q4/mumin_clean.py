from pathlib import Path
import pickle
import pandas as pd
import sys

DATA_DIR = Path(r"C:\Users\ivs5\Downloads\23yv276we2mll25fjakkfim2ml\23yv276we2mll25fjakkfim2ml\mumin")

# get filename from terminal
if len(sys.argv) < 2:
    print("Usage: python script.py <filename>")
    sys.exit(1)

filename = sys.argv[1]

with open(DATA_DIR / filename, "rb") as f:
    article_data = pickle.load(f)

print(type(article_data))

if isinstance(article_data, pd.DataFrame):
    print(article_data.head())
    article_data.to_csv(DATA_DIR / f"{Path(filename).stem}_fixed.csv", index=False)
    print(f"Saved to {Path(filename).stem}_fixed.csv")
else:
    print("Not a DataFrame.")
    print(article_data)