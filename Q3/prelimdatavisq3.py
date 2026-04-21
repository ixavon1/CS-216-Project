import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
import numpy as np

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

CURRENCY_MAP = {
    "AT": ("EUR", 1.08),
    "BE": ("EUR", 1.08),
    "CO": ("COP", 0.00025),
    "DE": ("EUR", 1.08),
    "HU": ("HUF", 0.0028),
    "IT": ("EUR", 1.08),
    "ES": ("EUR", 1.08),
    "SE": ("SEK", 0.096),
    "US": ("USD", 1.0),
}

def convert_to_usd(row):
    if pd.isna(row["spend_midpoint"]):
        return None
    currency, rate = CURRENCY_MAP.get(row["country"], ("USD", 1.0))
    return round(row["spend_midpoint"] * rate, 2)

df["spend_usd"] = df.apply(convert_to_usd, axis=1)
spend_df = df.dropna(subset=["spend_usd"])

COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Belgium", "CO": "Colombia",
    "DE": "Germany", "HU": "Hungary", "IT": "Italy",
    "ES": "Spain",   "SE": "Sweden",  "US": "United States"
}

countries = spend_df["country"].unique()
n_cols = 3
n_rows = -(-len(countries) // n_cols)  # ceiling division

fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 10))
axes = axes.flatten()

for i, country in enumerate(sorted(countries)):
    country_df = spend_df[spend_df["country"] == country]
    sns.barplot(
        data=country_df,
        x="label",
        y="spend_usd",
        hue="label",
        estimator="sum",
        errorbar=None,
        ax=axes[i],
        palette={"pro_immigration": "steelblue", "anti_immigration": "darkorange"}
    )
    axes[i].set_title(COUNTRY_NAMES.get(country, country))
    axes[i].set_xlabel("")
    axes[i].set_ylabel("Estimated Spend (USD)")
    axes[i].set_xticklabels(["Pro", "Anti"], rotation=0)
    axes[i].legend().remove()

# Hide any unused subplot panels
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

# Shared legend
handles = [
    plt.Rectangle((0,0),1,1, color="steelblue"),
    plt.Rectangle((0,0),1,1, color="darkorange")
]
fig.legend(handles, ["Pro-immigration", "Anti-immigration"],
           loc="lower right", fontsize=11)

fig.suptitle("Estimated Total Spend by Country and Stance (USD)", fontsize=14, y=1.02)
plt.tight_layout()
plt.show()

#chi square
# Build a contingency table of ad counts
contingency = pd.crosstab(df['country'], df['label'])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

print(f"Chi-square statistic: {chi2:.3f}")
print(f"P-value: {p_value:.4f}")
print(f"Degrees of freedom: {dof}")

#correlation test

# Enter the attitude data from the table manually
attitude_data = {
    "country": ["AT", "BE", "CO", "DE", "HU", "IT", "ES", "SE", "US"],
    "attitude_immigrants": [5.20, 5.16, 6.52, 5.42, 4.07, 5.59, 6.17, 5.07, 6.81],
    "attitude_refugees":   [5.04, 5.40, 6.55, 5.29, 4.42, 6.07, 6.62, 5.07, 6.70],
    "attitude_muslims":    [4.13, 4.91, None, 4.55, 3.61, 4.71, 4.83, 3.98, None],
    "sd_immigrants":       [2.44, 2.50, 2.33, 2.41, 2.48, 2.59, 2.45, 2.73, 2.67],
    "sd_refugees":         [2.44, 2.46, 2.13, 2.37, 2.42, 2.55, 2.32, 2.70, 2.63],
}

attitude_df = pd.DataFrame(attitude_data)

# Build your per-country ad summary
ad_summary = df.groupby('country').agg(
    total_ads=('label', 'count'),
    pro_ads=('label', lambda x: (x == 'pro_immigration').sum()),
    anti_ads=('label', lambda x: (x == 'anti_immigration').sum()),
    total_spend_usd=('spend_usd', 'sum'),
    pro_spend_usd=('spend_usd', lambda x: x[df.loc[x.index, 'label'] == 'pro_immigration'].sum()),
    anti_spend_usd=('spend_usd', lambda x: x[df.loc[x.index, 'label'] == 'anti_immigration'].sum()),
).reset_index()

# Add the log ratios from before
ad_summary['count_log_ratio'] = np.log(ad_summary['pro_ads'] / ad_summary['anti_ads'])
ad_summary['spend_log_ratio'] = np.log(ad_summary['pro_spend_usd'] / ad_summary['anti_spend_usd'])

# Merge with attitude data
combined = pd.merge(ad_summary, attitude_df, on='country')
print(combined)

def report_correlation(x, y, xlabel, ylabel):
    # Use Spearman rather than Pearson — your sample is only 9 countries
    # so normality assumptions don't hold, and Spearman is more robust
    mask = x.notna() & y.notna()
    r, p = stats.spearmanr(x[mask], y[mask])
    print(f"{xlabel} vs {ylabel}:")
    print(f"  Spearman r = {r:.3f}, p = {p:.4f}, n = {mask.sum()}")
    print()

# Does anti-immigration ad spend correlate with negative attitudes?
report_correlation(
    combined['anti_spend_usd'],
    combined['attitude_immigrants'],
    'Anti-immigration spend', 'Attitude toward immigrants'
)

# Does pro-immigration ad spend correlate with positive attitudes?
report_correlation(
    combined['pro_spend_usd'],
    combined['attitude_immigrants'],
    'Pro-immigration spend', 'Attitude toward immigrants'
)

# Does the pro/anti spend ratio correlate with attitudes?
report_correlation(
    combined['spend_log_ratio'],
    combined['attitude_immigrants'],
    'Spend log ratio (pro/anti)', 'Attitude toward immigrants'
)

# Count log ratio vs immigrant attitudes
report_correlation(
    combined['count_log_ratio'],
    combined['attitude_immigrants'],
    'Count log ratio (pro/anti)', 'Attitude toward immigrants'
)