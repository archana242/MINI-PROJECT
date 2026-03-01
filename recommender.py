import pandas as pd


# -------------------------------------------------
# Helper function: calculate engagement score
# -------------------------------------------------
def engagement_score(row):
    likes = row.get("likes", 0)
    comments = row.get("comments", 0)
    shares = row.get("shares", 0)
    saves = row.get("saves", 0)

    return likes + (2 * comments) + (2 * shares) + (2 * saves)


# -------------------------------------------------
# 1. POST DOCTOR
# -------------------------------------------------
def post_doctor(df):
    df = df.copy()
    insights = []

    df["engagement"] = df.apply(engagement_score, axis=1)
    avg_engagement = df["engagement"].mean()

    for index, row in df.iterrows():
        reason = ""
        fix = ""

        # Low performance
        if row["engagement"] < 0.7 * avg_engagement:
            post_type = row.get("post_type", "").lower()

            if post_type == "image":
                reason = "Image posts usually receive lower engagement."
                fix = "Try using reels or carousel posts."

            elif post_type == "video":
                reason = "Video did not hold audience attention."
                fix = "Add a strong hook in the first few seconds."

            elif post_type == "carousel":
                reason = "Carousel post did not encourage swipes."
                fix = "Improve the first slide to grab attention."

            else:
                reason = "Post did not perform well."
                fix = "Experiment with different content formats."

            if not row.get("hashtags"):
                reason += " No hashtags were used."
                fix += " Add 5–10 relevant hashtags."

        # High performance
        elif row["engagement"] > 1.3 * avg_engagement:
            reason = "This post performed very well."
            fix = "Repeat this content style and posting time."

        # Average performance
        else:
            reason = "Post performance was average."
            fix = "Improve caption quality, hashtags, or posting time."

        insights.append({
            "post_index": index,
            "engagement_score": int(row["engagement"]),
            "reason": reason,
            "fix": fix
        })

    return insights


# -------------------------------------------------
# 2. BEST POSTING SCHEDULE
# -------------------------------------------------
def best_posting_schedule(df):
    df = df.copy()

    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df = df.dropna(subset=["date_time"])

    df["day"] = df["date_time"].dt.day_name()
    df["hour"] = df["date_time"].dt.hour
    df["engagement"] = df.apply(engagement_score, axis=1)

    best_day = df.groupby("day")["engagement"].mean().idxmax()
    best_hour = df.groupby("hour")["engagement"].mean().idxmax()

    return {
        "best_day": best_day,
        "best_hour": f"{best_hour}:00",
        "suggestion": f"Post on {best_day} around {best_hour}:00 for better engagement."
    }


# -------------------------------------------------
# 3. PERFORMANCE DROP DETECTION
# -------------------------------------------------
def performance_drop_warning(df):
    df = df.copy()

    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df = df.dropna(subset=["date_time"])
    df = df.sort_values("date_time")

    df["engagement"] = df.apply(engagement_score, axis=1)

    if len(df) < 6:
        return {
            "warning": False,
            "message": "Not enough data to detect performance drop."
        }

    recent_avg = df.tail(5)["engagement"].mean()
    older_avg = df.head(len(df) - 5)["engagement"].mean()

    if recent_avg < 0.75 * older_avg:
        return {
            "warning": True,
            "message": "Engagement has dropped in recent posts.",
            "advice": "Try changing content type, posting time, or hashtags."
        }

    return {
        "warning": False,
        "message": "No significant performance drop detected."
    }
