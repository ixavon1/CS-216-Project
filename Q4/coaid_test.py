from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\ivs5\216\CoAID\05-01-2020")

# load one file
newsfake_tweets = pd.read_csv(DATA_DIR / "NewsFakeCOVID-19_tweets.csv")
newsreal_tweets = pd.read_csv(DATA_DIR / "NewsRealCOVID-19_tweets.csv")

# quick look
print(newsfake_tweets.head())

# count tweets per article
fake_counts = newsfake_tweets.groupby("index").size()
real_counts = newsreal_tweets.groupby("index").size()

print("Fake news article tweet counts:")
print(fake_counts.head())
print("Real news article tweet counts:")
print(real_counts.head())
print("Total fake news articles:", fake_counts.shape[0])
print("Total real news articles:", real_counts.shape[0])
print("Average tweets per fake news article:", fake_counts.mean())
print("Average tweets per real news article:", real_counts.mean())


import seaborn as sns

mean_df = pd.DataFrame({
    "type": ["Fake", "Real"],
    "mean_tweets": [fake_counts.mean(), real_counts.mean()]
})

sns.barplot(data=mean_df, x="type", y="mean_tweets")