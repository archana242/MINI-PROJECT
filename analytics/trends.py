import pandas as pd


def prepare_datetime(df):
    """
    Convert date_time column to datetime format.
    """
    df["date_time"] = pd.to_datetime(df["date_time"])
    return df


def generate_engagement_trend(df):
    """
    Generate daily engagement trend data.
    Returns dictionary with date and engagement list.
    """

    df = prepare_datetime(df)

    df["engagement_score"] = (
        df["likes"] +
        (2 * df["comments"]) +
        (3 * df["saves"])
    )

    df["date"] = df["date_time"].dt.date

    daily_trend = df.groupby("date")["engagement_score"].sum()

    return {
        "dates": [str(date) for date in daily_trend.index],
        "engagement": daily_trend.values.tolist()
    }


def detect_best_posting_day(df):
    """
    Detect best day of week based on average engagement.
    """

    df = prepare_datetime(df)

    df["engagement_score"] = (
        df["likes"] +
        (2 * df["comments"]) +
        (3 * df["saves"])
    )

    df["day_name"] = df["date_time"].dt.day_name()

    day_avg = df.groupby("day_name")["engagement_score"].mean()

    best_day = day_avg.idxmax()
    best_score = float(day_avg.max())

    return {
        "best_day": best_day,
        "average_engagement": round(best_score, 2)
    }


def detect_best_posting_time(df):
    """
    Detect best posting hour based on average engagement.
    """

    df = prepare_datetime(df)

    df["engagement_score"] = (
        df["likes"] +
        (2 * df["comments"]) +
        (3 * df["saves"])
    )

    df["hour"] = df["date_time"].dt.hour

    hour_avg = df.groupby("hour")["engagement_score"].mean()

    best_hour = int(hour_avg.idxmax())
    best_score = float(hour_avg.max())

    return {
        "best_hour": best_hour,
        "average_engagement": round(best_score, 2)
    }