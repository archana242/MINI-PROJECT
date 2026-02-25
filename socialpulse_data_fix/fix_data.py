import pandas as pd
import random
import os
import tkinter as tk
from tkinter import filedialog

# --- CONFIGURATION: The Hashtags to Add ---
hashtag_map = {
    'Technology': ['#tech', '#innovation', '#coding', '#future', '#ai', '#gadgets'],
    'Fitness': ['#fitness', '#gym', '#workout', '#health', '#fitfam', '#training'],
    'Travel': ['#travel', '#adventure', '#explore', '#wanderlust', '#trip', '#vacation'],
    'Food': ['#foodie', '#delicious', '#yummy', '#dinner', '#lunch', '#cooking'],
    'Fashion': ['#fashion', '#style', '#ootd', '#trend', '#model', '#beauty'],
    'Music': ['#music', '#song', '#artist', '#newmusic', '#vibe', '#concert'],
    'Beauty': ['#makeup', '#skincare', '#beautyhacks', '#glow', '#style'],
    'Lifestyle': ['#lifestyle', '#daily', '#motivation', '#inspiration', '#life'],
    'Comedy': ['#funny', '#comedy', '#humor', '#meme', '#lol'],
    'Photography': ['#photo', '#camera', '#shot', '#nature', '#art']
}

def assign_hashtags(row):
    # Get the category safely (convert to string just in case)
    category = str(row['content_category']) if pd.notna(row['content_category']) else 'Lifestyle'
    # Get relevant tags
    available_tags = hashtag_map.get(category, ['#viral', '#trending', '#explore'])
    # Pick 3 random ones
    return ", ".join(random.sample(available_tags, k=3))

# --- MAIN PROGRAM ---
print("🚀 Starting...")
print("👉 A window will pop up. Please select your 'Instagram_Analytics' CSV file.")

# 1. Open the File Picker Window
root = tk.Tk()
root.withdraw() # Hides the small empty window
file_path = filedialog.askopenfilename(title="Select your CSV File", filetypes=[("CSV Files", "*.csv")])

# 2. Check if user selected a file
if not file_path:
    print("❌ You cancelled the selection. Exiting.")
    exit()

print(f"✅ Loading file: {file_path}")

try:
    # 3. Read the CSV
    df = pd.read_csv(file_path)

    # 4. Add the Hashtags
    print("...Adding hashtags...")
    df['hashtag_list'] = df.apply(assign_hashtags, axis=1)

    # 5. Save the new file in the SAME folder as the old one
    folder_path = os.path.dirname(file_path)
    save_path = os.path.join(folder_path, 'socialpulse_final_dataset.csv')
    
    df.to_csv(save_path, index=False)
    
    print("-" * 30)
    print("🎉 SUCCESS! The fixed file is ready.")
    print(f"📂 Saved at: {save_path}")
    print("-" * 30)

except Exception as e:
    print(f"\n❌ An error occurred: {e}")
    print("Please take a photo of this error and show it to me.")