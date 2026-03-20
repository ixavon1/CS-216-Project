import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

df = pd.read_csv('immigration_ads.csv')
print(df.head())

# needed to make a variable to fix the legend
plt.figure(figsize=(8, 6))
g = sns.catplot(
    data=df,
    x='country',
    hue='label',
    kind='count',
    height=6,
    aspect=2,
)
g.set_axis_labels('Country', 'Number of Ads')
g.set_titles('Immigration Ads by Country and Category')
g.set_xticklabels(rotation=45)

plt.show()
