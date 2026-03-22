import os
import re
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session

# --- Analytics Imports ---
from analytics.metrics import calculate_totals, get_top_posts
try:
    from analytics.trends import detect_best_posting_time, analyze_hashtags, detect_performance_drops
except ImportError:
    detect_best_posting_time = analyze_hashtags = detect_performance_drops = lambda df: None

try:
    from analytics.recommender import generate_post_doctor_report, generate_weekly_schedule
except ImportError:
    generate_post_doctor_report = generate_weekly_schedule = lambda df: None

# --- VERCEL FIX: Global Cache ---
# Note: On Vercel, this will reset frequently. The code below handles this gracefully.
GLOBAL_CACHE = {
    "dashboard_data": None,
    "insights_data": None
}

app = Flask(__name__)
app.secret_key = "socialpulse_super_secret_key" 

# --- VERCEL FIX: Absolute Pathing ---
# 1. Grab the exact physical location of app.py on the Vercel server
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 2. Vercel ONLY allows writing to the /tmp folder. 
app.config['UPLOAD_FOLDER'] = '/tmp/uploads/'

# 3. Create the absolute path to your dataset
app.config['DEFAULT_DATASET'] = os.path.join(BASE_DIR, 'data', 'sample_dataset.csv')

# Create the temp directory for user uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Note: I REMOVED the os.makedirs('data') line that was here. 
# Vercel's main file system is read-only. As long as you pushed the 'data' 
# folder to GitHub, Vercel already has it!
def clean_and_standardize_csv(df):
    df.columns = df.columns.str.lower().str.strip()
    column_mappings = {
        'likes': ['like', 'likes', 'post likes', 'like count'],
        'comments': ['comment', 'comments', 'post comments', 'comment count'],
        'saves': ['save', 'saves', 'saved', 'post saves'],
        'reach': ['reach', 'post reach', 'accounts reached'],
        'post_datetime': ['publish time', 'date', 'time', 'post date', 'timestamp'],
        'caption': ['description', 'caption', 'text'],
        'post_type': ['post type', 'type', 'media type', 'format']
    }
    new_cols = {}
    for standard_name, possible_names in column_mappings.items():
        for col in df.columns:
            if col in possible_names: 
                new_cols[col] = standard_name
                break
    df = df.rename(columns=new_cols)
    
    for col in ['likes', 'comments', 'saves']:
        if col not in df.columns:
            df[col] = 0
            
    if 'hashtags' not in df.columns and 'caption' in df.columns:
        df['hashtags'] = df['caption'].apply(
            lambda x: ','.join(re.findall(r'#\w+', str(x))) if pd.notnull(x) else ""
        )
        
    if 'post_datetime' in df.columns:
        df['post_datetime'] = pd.to_datetime(df['post_datetime'], errors='coerce')
        df['date_time'] = df['post_datetime'] 
        if 'day_of_week' not in df.columns:
            df['day_of_week'] = df['post_datetime'].dt.day_name()
        if 'post_hour' not in df.columns:
            df['post_hour'] = df['post_datetime'].dt.hour
    else:
        df['post_datetime'] = pd.Timestamp.now()
        df['date_time'] = df['post_datetime']
        df['day_of_week'] = "Monday"
        df['post_hour'] = 12
        
    return df

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/download-template')
def download_template():
    template_path = os.path.join('data', 'template.csv')
    return send_file(template_path, as_attachment=True)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part in the request.")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No file selected for uploading.")
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            
            session['current_file'] = file.filename
            
            # Clear cache so the AI runs on the new data
            GLOBAL_CACHE["dashboard_data"] = None
            GLOBAL_CACHE["insights_data"] = None
            
            return redirect(url_for('dashboard'))
        else:
            flash("Please upload a valid CSV file.")
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/dashboard')
def dashboard():
    filename = session.get('current_file')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) if filename else app.config['DEFAULT_DATASET']
    
    # --- VERCEL FIX: Check if Vercel deleted the temp file ---
    if not os.path.exists(file_path):
        file_path = app.config['DEFAULT_DATASET']
        filename = "sample_dataset.csv" # Update UI to reflect we fell back
        GLOBAL_CACHE["dashboard_data"] = None # Force recalculation

    if GLOBAL_CACHE["dashboard_data"] is None:
        try:
            df = pd.read_csv(file_path)
            df = clean_and_standardize_csv(df)
            
            totals = calculate_totals(df)
            top_posts = get_top_posts(df)
            metrics_data = {"totals": totals, "top_posts": top_posts}
            
            best_time_data = detect_best_posting_time(df)
            hashtag_data = analyze_hashtags(df)
            drop_alerts = detect_performance_drops(df)
            schedule = generate_weekly_schedule(df)
            post_doctor = generate_post_doctor_report(df)
            
            GLOBAL_CACHE["dashboard_data"] = {
                "metrics": metrics_data,
                "best_time": best_time_data,
                "hashtags": hashtag_data,
                "alerts": drop_alerts,
                "schedule": schedule,
                "doctor": post_doctor,
                "current_file": filename
            }
            
        except Exception as e:
            return f"Error processing data: {str(e)}", 500

    saved_data = GLOBAL_CACHE["dashboard_data"]
    
    return render_template(
        'dashboard.html',
        metrics=saved_data["metrics"],
        best_time=saved_data["best_time"],
        hashtags=saved_data["hashtags"],
        alerts=saved_data["alerts"],
        schedule=saved_data["schedule"],
        doctor=saved_data["doctor"],
        current_file=saved_data["current_file"]
    )

@app.route('/insights')
def insights():
    filename = session.get('current_file')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) if filename else app.config['DEFAULT_DATASET']
    
    # --- VERCEL FIX: Check if Vercel deleted the temp file ---
    if not os.path.exists(file_path):
        file_path = app.config['DEFAULT_DATASET']
        filename = "sample_dataset.csv"
        GLOBAL_CACHE["insights_data"] = None

    if GLOBAL_CACHE["insights_data"] is None:
        try:
            df = pd.read_csv(file_path)
            df = clean_and_standardize_csv(df)
            
            from analytics.trends import detect_best_posting_time, analyze_hashtags, detect_performance_drops
            from analytics.recommender import generate_weekly_schedule
            
            best_time_data = detect_best_posting_time(df)
            hashtag_data = analyze_hashtags(df)
            
            if isinstance(hashtag_data, dict):
                for key in ['top', 'worst']:
                    if key in hashtag_data:
                        flattened = []
                        for item in hashtag_data[key]:
                            flattened.extend([t.strip() for t in str(item).split(',') if t.strip()])
                        hashtag_data[key] = list(set(flattened))[:8]

            drop_alerts = detect_performance_drops(df)
            schedule = generate_weekly_schedule(df) 
            
            GLOBAL_CACHE["insights_data"] = {
                "best_time": best_time_data,
                "hashtags": hashtag_data,
                "alerts": drop_alerts,
                "schedule": schedule,
                "current_file": filename
            }
            
        except Exception as e:
            GLOBAL_CACHE["insights_data"] = {
                "best_time": {"best_hour": "N/A"},
                "hashtags": {"top": [], "worst": []},
                "alerts": ["Not enough data to detect trends."],
                "schedule": {"Error": "Need more data"},
                "current_file": filename
            }

    saved_data = GLOBAL_CACHE["insights_data"]

    return render_template(
        'insights.html', 
        best_time=saved_data["best_time"], 
        hashtags=saved_data["hashtags"], 
        alerts=saved_data["alerts"], 
        schedule=saved_data["schedule"], 
        current_file=saved_data["current_file"]
    )

@app.route('/postdetails')
def postdetails():
    filename = session.get('current_file')
    post_index = request.args.get('post_index', 0, type=int) 
    
    selected_post = None
    tips = {"content_type": "N/A", "momentum": "N/A"}
    verdict = "Not enough data to generate a verdict."
    
    if GLOBAL_CACHE.get("dashboard_data") and GLOBAL_CACHE["dashboard_data"].get("metrics"):
        top_posts = GLOBAL_CACHE["dashboard_data"]["metrics"]["top_posts"]
        if top_posts and 0 <= post_index < len(top_posts):
            selected_post = top_posts[post_index]

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) if filename else app.config['DEFAULT_DATASET']
    
    # --- VERCEL FIX: Check if Vercel deleted the temp file ---
    if not os.path.exists(file_path):
        file_path = app.config['DEFAULT_DATASET']
        filename = "sample_dataset.csv"

    try:
        df = pd.read_csv(file_path)
        df = clean_and_standardize_csv(df)
        
        if not selected_post:
            from analytics.metrics import get_top_posts
            top_posts = get_top_posts(df)
            if top_posts and 0 <= post_index < len(top_posts):
                selected_post = top_posts[post_index]
            elif top_posts:
                selected_post = top_posts[0]
                
        if selected_post and not df.empty:
            likes = int(selected_post.get('likes', 0))
            comments = int(selected_post.get('comments', 0))
            saves = int(selected_post.get('saves', 0))
            
            # Use max(1, ...) to prevent division by zero errors
            median_likes = max(1, df['likes'].median() if 'likes' in df.columns else 1)
            median_comments = max(1, df['comments'].median() if 'comments' in df.columns else 1)
            median_saves = max(1, df['saves'].median() if 'saves' in df.columns else 1)

            # --- THE NEW MATH: FIND THE BIGGEST SPIKE ---
            save_ratio = saves / median_saves
            comment_ratio = comments / median_comments
            like_ratio = likes / median_likes
            
            best_metric = max(save_ratio, comment_ratio, like_ratio)

            if best_metric == save_ratio and save_ratio > 1.2: 
                verdict = f" High Value Content. This post generated {int((save_ratio-1)*100)}% more saves than your historical median ({int(median_saves)} saves). Your audience found this highly educational."
            elif best_metric == comment_ratio and comment_ratio > 1.2:
                verdict = f"Conversation Starter. Comments are {int((comment_ratio-1)*100)}% above your baseline median of {int(median_comments)}. Reply to these quickly to maximize algorithmic reach."
            elif best_metric == like_ratio and like_ratio > 1.2:
                verdict = f"Strong Reach. This outperformed your average like baseline by {int((like_ratio-1)*100)}%. The visual hook here worked perfectly."
            else:
                verdict = "Data-Driven Analysis: Consistent Performance. This post aligns perfectly with your normal engagement baseline. Try experimenting with a stronger Call-To-Action (CTA) next time to push it even further."

            # --- THE NEW TIPS: UNIQUE FOR EACH RANK ---
            rank = post_index + 1
            if rank == 1:
                tips['content_type'] = "This is your absolute best format. Double down on this exact style."
                tips['momentum'] = "Incredible reach. Pin this to your profile so new visitors see it first."
            elif rank == 2:
                tips['content_type'] = "Highly engaging topic. Consider turning this exact theme into a 3-part series."
                tips['momentum'] = "Great traction. Share this to your Story today to catch anyone who missed it."
            elif rank == 3:
                tips['content_type'] = "Strong educational value. Repurpose this content into a carousel post next month."
                tips['momentum'] = "Algorithm favorite. Try posting at this exact same time next week."
            elif rank == 4:
                tips['content_type'] = "Solid performance. Experiment with trending audio to boost this format's reach further."
                tips['momentum'] = "Good engagement speed. Reply to all comments to keep the algorithm pushing it."
            else:
                tips['content_type'] = "Consistent winner. Test a slightly shorter caption next time to see if retention increases."
                tips['momentum'] = "Steady growth. Engage with 5 accounts in your niche before your next post."

    except Exception as e:
        print(f"CRITICAL ERROR IN POSTDETAILS: {e}")

    return render_template('postdetails.html', post=selected_post, rank=post_index + 1, tips=tips, verdict=verdict, current_file=filename)
if __name__ == '__main__':
    app.run(debug=True, port=5000)