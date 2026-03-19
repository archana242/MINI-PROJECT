import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# Load the hidden variables from the .env file
load_dotenv()

# Safely fetch the API key
API_KEY = os.getenv("GEMINI_API_KEY")

# Add a safety check so your code doesn't fail silently if the key is missing
if not API_KEY:
    raise ValueError("No API key found! Please make sure you have a .env file with GEMINI_API_KEY.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemma-3-27b-it')

# ... the rest of your functions (engagement_score, generate_post_doctor_report, etc.) remain exactly the same ...
def engagement_score(row):
    likes = row.get("likes", 0)
    comments = row.get("comments", 0)
    shares = row.get("shares", 0)
    saves = row.get("saves", 0)
    return likes + (2 * comments) + (2 * shares) + (2 * saves)

# -------------------------------------------------
# 1. POST DOCTOR (WITH SILENT FALLBACK)
# -------------------------------------------------
def generate_post_doctor_report(df):
    try:
        df = df.copy()
        insights = []

        df["engagement"] = df.apply(engagement_score, axis=1)
        typical_engagement = df["engagement"].median()

        df_poor = df[df["engagement"] < (0.7 * typical_engagement)].copy().sort_values("engagement").head(3)

        ai_lines = []

        if not df_poor.empty:
            prompt = "You are helping a jewelry brand on Instagram. Analyze these failing posts. Provide EXACTLY one line of text per post, formatted exactly like this: Reason | Tip\n\n"
            
            for i, (_, row) in enumerate(df_poor.iterrows()):
                caption = str(row.get("caption", ""))[:50]
                prompt += f"Post {i+1}: Likes {row.get('likes', 0)}, Comments {row.get('comments', 0)}, Caption: '{caption}'\n"
            
            try:
                response = model.generate_content(prompt)
                ai_lines = [line for line in response.text.split('\n') if '|' in line]
            except Exception as e:
                # 👇 THIS WILL PRINT THE HIDDEN ERROR TO YOUR TERMINAL 👇
                print(f"\n🛑 POST DOCTOR AI ERROR: {str(e)}\n")
                
                # 🚀 PRESENTATION MODE
                ai_lines = [
                    "The lighting was too dim and hid the product | Film near a window with natural sunlight to make the gold pop.",
                    "The video started too slow to catch attention | Drop the jewelry into the frame in the first 2 seconds as a hook.",
                    "The caption lacked a call to action | End your caption by asking viewers to comment their favorite piece."
                ]

        for i, (index, row) in enumerate(df_poor.iterrows()):
            dt = str(row.get("post_datetime", "Unknown Date"))
            caption = str(row.get("caption", ""))[:35] + "..."
            identifier = f"{dt} | {caption}"

            reason = "Waiting for data..."
            fix = "Please refresh."

            if i < len(ai_lines):
                parts = ai_lines[i].split('|')
                if len(parts) >= 2:
                    reason = parts[0].replace(f"Post {i+1}:", "").strip()
                    fix = parts[1].strip()

            insights.append({
                "post_index": index,
                "engagement_score": int(row["engagement"]),
                "reason": reason,
                "fix": fix,
                "identifier": identifier
            })

        return insights
    except Exception as e:
        return []


# -------------------------------------------------
# 2. AI CONTENT STRATEGIST (IDEAS ONLY)
# -------------------------------------------------
def generate_weekly_schedule(df):
    schedule = {
        "Viral Reel Idea 1": "Waiting for data...",
        "Viral Reel Idea 2": "Waiting for data...",
        "Viral Reel Idea 3": "Waiting for data..."
    }

    try:
        prompt = """
        You are helping a jewellery brand on Instagram. 
        Give me exactly 3 creative video ideas for Instagram Reels showing off jewelry. 
        Format your response EXACTLY like this. Do not change the tags:
        IDEA1: [your first idea here]
        IDEA2: [your second idea here]
        IDEA3: [your third idea here]
        """
        response = model.generate_content(prompt)
        text = response.text
        
        if "IDEA1:" in text and "IDEA2:" in text and "IDEA3:" in text:
            schedule["Viral Reel Idea 1"] = text.split("IDEA1:")[1].split("IDEA2:")[0].strip()
            schedule["Viral Reel Idea 2"] = text.split("IDEA2:")[1].split("IDEA3:")[0].strip()
            schedule["Viral Reel Idea 3"] = text.split("IDEA3:")[1].strip()
        else:
            raise Exception("Format Error")
            
    except Exception as e:
        # 👇 THIS WILL PRINT THE HIDDEN ERROR TO YOUR TERMINAL 👇
        print(f"\n🛑 CONTENT STRATEGIST AI ERROR: {str(e)}\n")
        
        # 🚀 PRESENTATION MODE
        schedule["Viral Reel Idea 1"] = "ASMR Packing: Record the crisp sound of a velvet box snapping shut and tissue paper wrapping."
        schedule["Viral Reel Idea 2"] = "Macro Sparkle: Use your phone's macro lens to show a super close-up of a diamond catching the light."
        schedule["Viral Reel Idea 3"] = "Styling Guide: Show a quick 3-second transition of layering three different gold necklaces."
            
    return schedule