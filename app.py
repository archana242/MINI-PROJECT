import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash

# Import functions from your analytics package
# Note: Ensure your team defines these exact function names in the analytics module.
from analytics.metrics import calculate_overview_metrics
from analytics.trends import detect_best_posting_time, analyze_hashtags, detect_performance_drops
from analytics.recommender import generate_post_doctor_report, generate_weekly_schedule

app = Flask(__name__)

# Basic configurations
app.secret_key = "socialpulse_super_secret_key" # Required for flash messages
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['DEFAULT_DATASET'] = 'data/sample_dataset.csv'

# Ensure the upload and data directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)


@app.route('/')
def home():
    """Renders the home page."""
    return render_template('home.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Handles CSV dataset uploads."""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash("No file part in the request.")
            return redirect(request.url)
        
        file = request.files['file']
        
        # If the user does not select a file, the browser submits an empty file without a filename
        if file.filename == '':
            flash("No file selected for uploading.")
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            # Redirect to the dashboard and pass the uploaded filename as a URL parameter
            return redirect(url_for('dashboard', filename=file.filename))
        else:
            flash("Please upload a valid CSV file.")
            return redirect(request.url)

    # Render upload form on GET request
    return render_template('upload.html')


@app.route('/dashboard')
def dashboard():
    """
    Loads the dataset (uploaded or default), calls analytics modules, 
    and renders the dashboard template.
    """
    # 1. Determine which dataset to load
    filename = request.args.get('filename')
    
    if filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            flash("Uploaded file not found. Falling back to default dataset.")
            file_path = app.config['DEFAULT_DATASET']
    else:
        file_path = app.config['DEFAULT_DATASET']

    # 2. Read dataset using pandas
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return f"Error: Dataset not found at {file_path}. Please ensure it exists.", 404
    except Exception as e:
        return f"Error reading the dataset: {str(e)}", 500

    # 3. Call functions from analytics files (Rule-based logic)
    # Passing the DataFrame to the analytics functions created by your team
    try:
        metrics_data = calculate_overview_metrics(df)
        best_time_data = detect_best_posting_time(df)
        hashtag_data = analyze_hashtags(df)
        drop_alerts = detect_performance_drops(df)
        post_doctor = generate_post_doctor_report(df)
        schedule = generate_weekly_schedule(df)
    except Exception as e:
        # Catch errors if the analytics team hasn't implemented these functions yet
        return f"Analytics processing error: {str(e)}. Check your analytics/ files.", 500

    # 4. Pass results to the dashboard template
    return render_template(
        'dashboard.html',
        data_source=filename if filename else 'sample_dataset.csv',
        metrics=metrics_data,
        best_time=best_time_data,
        hashtags=hashtag_data,
        alerts=drop_alerts,
        doctor=post_doctor,
        schedule=schedule
    )


if __name__ == '__main__':
    # Run the app in debug mode for development
    app.run(debug=True, port=5000)