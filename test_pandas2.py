import pandas as pd
df = pd.read_csv("e:/xueqiuSc/data/雪月霜.csv")
long_posts = df[df['正文'].str.len() > 140]
print("Long posts (>140 chars):", len(long_posts))
if not long_posts.empty:
    print("Sample long post length:", len(long_posts.iloc[0]['正文']))
    print("Sample excerpt:", long_posts.iloc[0]['正文'][:50], "...")
