import pandas as pd


def load_data(file_path):
    """
    Load CSV or Excel file into pandas DataFrame.
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    return df


def calculate_totals(df):
    """
    Calculate total posts, likes, comments and saves.
    """
    totals = {
        "total_posts": int(len(df)),  # <-- We added this line to count the posts!
        "total_likes": int(df["likes"].sum()),
        "total_comments": int(df["comments"].sum()),
        "total_saves": int(df["saves"].sum())
    }

    return totals

def calculate_engagement_score(df):
    """
    engagement_score = likes + (2 * comments) + (3 * saves)
    """
    df["engagement_score"] = (
        df["likes"] +
        (2 * df["comments"]) +
        (3 * df["saves"])
    )

    return df


def get_top_posts(df, top_n=5):
    """
    Return top N posts based on engagement score.
    Handles missing columns gracefully!
    """

    if "engagement_score" not in df.columns:
        df = calculate_engagement_score(df)

    top_posts = df.sort_values(
        by="engagement_score",
        ascending=False
    ).head(top_n)

    # BULLETPROOF LOGIC: Only ask for columns that actually exist in the uploaded CSV
    desired_columns = ["date_time", "post_type", "likes", "comments", "saves", "engagement_score"]
    available_columns = [col for col in desired_columns if col in df.columns]

    result = top_posts[available_columns].to_dict(orient="records")

    return result