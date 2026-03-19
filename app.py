import os
import re
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session

from analytics.metrics import calculate_totals, get_top_posts
# Add this near the top!
GLOBAL_CACHE = {
    "dashboard_data": None,
    "insights_data": None
}
try:
    from analytics.trends import detect_best_posting_time, analyze_hashtags, detect_performance_drops
except ImportError:
    detect_best_posting_time = analyze_hashtags = detect_performance_drops = lambda df: None

try:
    from analytics.recommender import generate_post_doctor_report, generate_weekly_schedule
except ImportError:
    generate_post_doctor_report = generate_weekly_schedule = lambda df: None

app = Flask(__name__)
app.secret_key = "socialpulse_super_secret_key" 
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['DEFAULT_DATASET'] = 'data/sample_dataset.csv'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

def clean_and_standardize_csv(df):
    df.columns = df.columns.str.lower().str.strip()
    column_mappings = {
        'likes': ['like', 'likes', 'post likes', 'like count'],
        'comments': ['comment', 'comments', 'post comments', 'comment count'],
        'saves': ['save', 'saves', 'saved', 'post saves'],
        'reach': ['reach', 'post reach', 'accounts reached'],
        'post_datetime': ['publish time', 'date', 'time', 'post date', 'timestamp'],
        'caption': ['description', 'caption', 'text'],
        'post_type': ['post type', 'type', 'media type', 'format'] # <-- ADDED THIS!
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
        df['date_time'] = df['post_datetime'] # <-- ADDED THIS SO METRICS.PY CAN READ IT!
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
            
            # Tell Flask Session to permanently remember this file
            session['current_file'] = file.filename
            
            # --- THE CACHE WIPE FIX ---
            # Clear the memory so the app knows to run the AI on the new data!
            GLOBAL_CACHE["dashboard_data"] = None
            GLOBAL_CACHE["insights_data"] = None
            
            return redirect(url_for('dashboard'))
        else:
            flash("Please upload a valid CSV file.")
            return redirect(request.url)
    return render_template('upload.html')
@app.route('/dashboard')
def dashboard():
    # 1. If we haven't loaded the data yet, do the heavy lifting!
    if GLOBAL_CACHE["dashboard_data"] is None:
        
        filename = session.get('current_file')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) if filename else app.config['DEFAULT_DATASET']
        
        # If the file somehow doesn't exist, fall back to default
        if not os.path.exists(file_path):
            file_path = app.config['DEFAULT_DATASET']
            
        try:
            # Read and clean the data ONCE
            df = pd.read_csv(file_path)
            df = clean_and_standardize_csv(df)
            
            # Run all math and AI analytics ONCE
            totals = calculate_totals(df)
            top_posts = get_top_posts(df)
            metrics_data = {"totals": totals, "top_posts": top_posts}
            
            best_time_data = detect_best_posting_time(df)
            hashtag_data = analyze_hashtags(df)
            drop_alerts = detect_performance_drops(df)
            schedule = generate_weekly_schedule(df)
            post_doctor = generate_post_doctor_report(df)
            
            # Save EVERYTHING to memory so we never have to run it again!
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

    # 2. Grab the fully processed data from memory instantly
    saved_data = GLOBAL_CACHE["dashboard_data"]
    
    # 3. Send it to the webpage
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
    # 1. If we haven't loaded the data yet, do the heavy lifting!
    if GLOBAL_CACHE["insights_data"] is None:
        
        filename = session.get('current_file')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) if filename else app.config['DEFAULT_DATASET']
        
        if not os.path.exists(file_path):
            file_path = app.config['DEFAULT_DATASET']
            
        try:
            # Read and clean the data ONCE
            df = pd.read_csv(file_path)
            df = clean_and_standardize_csv(df)
            
            from analytics.trends import detect_best_posting_time, analyze_hashtags, detect_performance_drops
            from analytics.recommender import generate_weekly_schedule
            
            best_time_data = detect_best_posting_time(df)
            hashtag_data = analyze_hashtags(df)
            
            # UI FIX: Flatten and clean up the Hashtag display!
            if isinstance(hashtag_data, dict):
                for key in ['top', 'worst']:
                    if key in hashtag_data:
                        flattened = []
                        for item in hashtag_data[key]:
                            flattened.extend([t.strip() for t in str(item).split(',') if t.strip()])
                        hashtag_data[key] = list(set(flattened))[:8]

            drop_alerts = detect_performance_drops(df)
            schedule = generate_weekly_schedule(df) # This calls the AI
            
            # Save EVERYTHING to memory so we never have to run it again!
            GLOBAL_CACHE["insights_data"] = {
                "best_time": best_time_data,
                "hashtags": hashtag_data,
                "alerts": drop_alerts,
                "schedule": schedule,
                "current_file": filename
            }
            
        except Exception as e:
            # If there is an error, save the safe fallback data to memory
            GLOBAL_CACHE["insights_data"] = {
                "best_time": {"best_hour": "N/A"},
                "hashtags": {"top": [], "worst": []},
                "alerts": ["Not enough data to detect trends."],
                "schedule": {"Error": "Need more data"},
                "current_file": filename
            }

    # 2. Grab the fully processed data from memory instantly
    saved_data = GLOBAL_CACHE["insights_data"]

    # 3. Send it to the webpage
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
    
    # 1. Grab the exact number from the URL
    post_index = request.args.get('post_index', 0, type=int) 
    
    # 2. Set up our default text just in case
    selected_post = None
    tips = {"content_type": "N/A", "momentum": "N/A"}
    verdict = "Not enough data to generate a verdict."
    
    # 3. THE FIX: Grab the EXACT same list of posts the dashboard is using from memory!
    if GLOBAL_CACHE.get("dashboard_data") and GLOBAL_CACHE["dashboard_data"].get("metrics"):
        top_posts = GLOBAL_CACHE["dashboard_data"]["metrics"]["top_posts"]
        if top_posts and 0 <= post_index < len(top_posts):
            selected_post = top_posts[post_index]

    # 4. We still need to load the CSV quickly just to get the 'median' averages for the math
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) if filename else app.config['DEFAULT_DATASET']
    if not os.path.exists(file_path):
        file_path = app.config['DEFAULT_DATASET']

    try:
        df = pd.read_csv(file_path)
        df = clean_and_standardize_csv(df)
        
        # Failsafe: If the cache was empty, calculate the posts manually
        if not selected_post:
            from analytics.metrics import get_top_posts
            top_posts = get_top_posts(df)
            if top_posts and 0 <= post_index < len(top_posts):
                selected_post = top_posts[post_index]
            elif top_posts:
                selected_post = top_posts[0]
                
        # 5. Generate the Smart Analysis using the specific selected_post
        if selected_post and not df.empty:
            likes = int(selected_post.get('likes', 0))
            comments = int(selected_post.get('comments', 0))
            saves = int(selected_post.get('saves', 0))
            
            median_likes = df['likes'].median() if 'likes' in df.columns else 0
            median_comments = df['comments'].median() if 'comments' in df.columns else 0
            median_saves = df['saves'].median() if 'saves' in df.columns else 0

            if saves > (median_saves * 1.5) and saves > 0: 
                verdict = f"Smart Analysis: High Value Content. This post generated 50%+ more saves than your historical median ({int(median_saves)} saves). Your audience found this highly educational."
            elif comments > (median_comments * 1.5) and comments > 0:
                verdict = f"Smart Analysis: Conversation Starter. Comments are significantly above your baseline median of {int(median_comments)}. Reply to these quickly to maximize algorithmic reach."
            elif likes > (median_likes * 1.2) and likes > 0:
                verdict = f"Smart Analysis: Strong Reach. This outperformed your average like baseline by over 20%. The visual hook here worked perfectly."
            else:
                verdict = "Smart Analysis: Consistent Performance. This post aligns with your normal engagement baseline. Try experimenting with a stronger Call-To-Action (CTA) next time to break past your average."

            # Generate the Tips based on the Rank (1st, 2nd, 3rd, etc.)
            rank = post_index + 1
            if rank == 1:
                tips['content_type'] = "This is your absolute best format. Double down on this exact style."
                tips['momentum'] = "Incredible reach. Pin this to your profile so new visitors see it first."
            elif rank <= 3:
                tips['content_type'] = "Highly engaging content. Consider turning this topic into a Reel to reach non-followers."
                tips['momentum'] = "Great traction. Try posting at this exact same time next week."
            else:
                tips['content_type'] = "Experiment with shorter captions or trending audio to boost this format's reach."
                tips['momentum'] = "Performance is average. Try engaging with other accounts for 15 mins before posting."

    except Exception as e:
        print(f"CRITICAL ERROR IN POSTDETAILS: {e}")

    return render_template('postdetails.html', post=selected_post, rank=post_index + 1, tips=tips, verdict=verdict, current_file=filename)
if __name__ == '__main__':
    app.run(debug=True, port=5000)