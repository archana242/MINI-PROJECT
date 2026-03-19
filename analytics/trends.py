import pandas as pd

def prepare_datetime(df):
    """
    Convert the correct date column to datetime format.
    Checks for multiple names so the app doesn't crash!
    """
    if "post_datetime" in df.columns:
        df["date_time"] = pd.to_datetime(df["post_datetime"], errors='coerce')
    elif "date_time" in df.columns:
        df["date_time"] = pd.to_datetime(df["date_time"], errors='coerce')
    else:
        # Failsafe
        df["date_time"] = pd.Timestamp.now()
    return df

def detect_best_posting_time(df):
    """Calculates the best hour to post based on historical engagement."""
    try:
        df = prepare_datetime(df)
        df["engagement_score"] = df.get("likes", 0) + (2 * df.get("comments", 0)) + (3 * df.get("saves", 0))
        
        df["hour"] = df["date_time"].dt.hour
        hour_avg = df.groupby("hour")["engagement_score"].mean()
        
        best_hour = int(hour_avg.idxmax())
        best_score = float(hour_avg.max())
        
        formatted_hour = f"{best_hour % 12 or 12} {'AM' if best_hour < 12 else 'PM'}"
        return {"best_hour": formatted_hour, "average_engagement": round(best_score, 2)}
    except Exception as e:
        return {"best_hour": "N/A", "average_engagement": 0}

# ==========================================
# 🚀 NEW: THE HASHTAG ROI ANALYZER
# ==========================================
def analyze_hashtags(df):
    """Calculates which hashtags bring the highest and lowest engagement."""
    try:
        if 'hashtags' not in df.columns or df['hashtags'].astype(str).str.strip().eq('').all():
            return {"top": [], "worst": []}

        df["engagement_score"] = df.get("likes", 0) + (2 * df.get("comments", 0)) + (3 * df.get("saves", 0))
        
        hashtag_engagements = {}
        
        # Loop through every post
        for index, row in df.iterrows():
            tags = str(row['hashtags']).split(',')
            eng = row['engagement_score']
            
            # Group engagement scores by individual hashtag
            for tag in tags:
                tag = tag.strip()
                if tag and tag.startswith('#'):
                    if tag not in hashtag_engagements:
                        hashtag_engagements[tag] = []
                    hashtag_engagements[tag].append(eng)

        # Calculate the average engagement for each tag
        tag_avgs = {tag: sum(engs)/len(engs) for tag, engs in hashtag_engagements.items() if len(engs) > 0}
        
        if not tag_avgs:
            return {"top": [], "worst": []}

        # Sort from highest engagement to lowest
        sorted_tags = sorted(tag_avgs.items(), key=lambda x: x[1], reverse=True)
        
        # Grab the top 8 and bottom 8
        top_tags = [tag for tag, val in sorted_tags[:8]]
        
        # Only show worst tags if they have a decent amount of tags to compare against
        worst_tags = [tag for tag, val in sorted_tags[-8:]] if len(sorted_tags) > 8 else []

        return {"top": top_tags, "worst": worst_tags}
    except Exception as e:
        return {"top": [], "worst": []}

# ==========================================
# 🚨 NEW: PERFORMANCE DROP ALERTS
# ==========================================
# ==========================================
# 🚨 PERFORMANCE DROP ALERTS (PRO UPGRADE)
# ==========================================
def detect_performance_drops(df):
    """Detects if the most recent post severely underperformed the baseline."""
    try:
        df = prepare_datetime(df)
        df = df.sort_values("date_time", ascending=True)

        alerts = []
        if len(df) < 3:
            return ["Not enough data to detect trends."]

        recent_likes = df['likes'].iloc[-1]
        
        # THE FIX: We use Median here to ignore viral outliers!
        typical_likes = df['likes'].iloc[:-1].median()

        # Trigger alert if the newest post dropped 30% below the normal median
        if recent_likes < (typical_likes * 0.7):
            alerts.append(f"Drop Alert: Your latest post got {int(recent_likes)} likes, which is over 30% below your typical baseline ({int(typical_likes)}). Check if your hashtags or posting time changed.")

        return alerts
    except Exception as e:
        return ["Not enough data to detect trends."]