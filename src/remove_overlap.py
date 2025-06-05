"""
Script to manage overlapping chapters in Jupyter notebook files from Google Drive.
This script extracts headings, identifies overlaps using ChatGPT, and manages chapter numbering.
"""

PROMPT_DOC_ID = "1UHefUKZlUDyxJJ76Wmx9Di0c9U6d67Ni3JB9ofZr1KU"  # Replace with your prompt document ID

import os
import sys
import json
import re
from time import sleep

# Add current directory to path for importing myclasses
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from myclasses import (
    GoogleDriveHandler, TranslationHandler,
    KEY_FILE, SCOPES, OPENAI_API_KEY,
    DESTINATION_FOLDER, TRANSLATED_FOLDER
)

# List of notebook file IDs to process
NOTEBOOK_FILE_IDS = [
    "1ooEwVOpGqf7YIlCgUCGyy14TdQrH4X4O",
    "1ETG3nB589iloD8PlurtCtUNPb1mHJtgI",
    "1aHBqz8Kp00uzMDoJQzQi7dF4yTWxEfx_",
    "1vW6h2n_et-Zu_u0CGiCL-x4O4SFyi2Eh",
]

def download_notebook(drive_handler, file_id, destination_folder):
    """Download a notebook file from Google Drive."""
    file_metadata = drive_handler.service.files().get(fileId=file_id).execute()
    file_name = file_metadata['name']
    
    print(f"📥 Downloading notebook: {file_name}")
    
    request = drive_handler.service.files().get_media(fileId=file_id)
    os.makedirs(destination_folder, exist_ok=True)
    file_path = os.path.join(destination_folder, file_name)
    
    with open(file_path, 'wb') as f:
        downloader = drive_handler.service.files().get_media(fileId=file_id)
        f.write(downloader.execute())
    
    return file_path, file_name

def extract_headings_from_notebook(file_path):
    """
    Extract all headings (## format) from a Jupyter notebook.
    Returns a list of dictionaries with heading info and cell indices.
    """
    print(f"📖 Extracting headings from: {file_path}")
    headings = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

        for cell_idx, cell in enumerate(notebook['cells']):
            if cell['cell_type'] == 'markdown':
                content = ''.join(cell['source'])
                
                # Find all headings with ## format
                heading_matches = re.finditer(r'^##\s*(.+)', content, re.MULTILINE)
                
                for match in heading_matches:
                    heading_text = match.group(1).strip()
                    headings.append({
                        'text': heading_text,
                        'cell_index': cell_idx,
                        'full_content': content,
                        'notebook_path': file_path
                    })

    print(f"✅ Found {len(headings)} headings")
    return headings

def compare_headings_with_chatgpt(translator, all_notebook_headings):
    """
    Use ChatGPT to identify overlapping topics between notebooks.
    """
    print("🤖 Analyzing headings for overlaps using ChatGPT...")
    
    # Prepare the comparison prompt
    comparison_text = "Please analyze these notebook headings for overlapping topics:\n\n"
    
    for notebook_path, headings in all_notebook_headings.items():
        notebook_name = os.path.basename(notebook_path)
        comparison_text += f"**{notebook_name}:**\n"
        for i, heading in enumerate(headings, 1):
            comparison_text += f"{i}. {heading['text']}\n"
        comparison_text += "\n"
    
    comparison_text += """
Please identify any overlapping or duplicate topics between these notebooks. 
For each overlap found, provide:
1. The specific headings that overlap
2. Which notebooks they appear in
3. A brief explanation of why they overlap
4. Recommendation on which occurrence should be kept (usually the first one)

Format your response as a clear list of overlaps.
"""
    
    try:
        overlap_analysis = translator.translate_text(
            comparison_text, 
            target_language="English",
            prompt_text="You are analyzing notebook chapter headings for overlaps. Provide clear, actionable recommendations."
        )
        return overlap_analysis
    except Exception as e:
        print(f"❌ Error analyzing overlaps: {str(e)}")
        return None

def parse_overlap_suggestions(overlap_analysis):
    """
    Parse ChatGPT's overlap analysis into actionable suggestions.
    This is a simplified parser - you might need to adjust based on ChatGPT's response format.
    """
    suggestions = []
    
    # This is a basic implementation - you may need to adjust based on actual ChatGPT responses
    lines = overlap_analysis.split('\n')
    current_overlap = None
    
    for line in lines:
        line = line.strip()
        if line and ('overlap' in line.lower() or 'duplicate' in line.lower()):
            if current_overlap:
                suggestions.append(current_overlap)
            current_overlap = {'description': line, 'recommendations': []}
        elif current_overlap and line.startswith(('-', '•', '*')):
            current_overlap['recommendations'].append(line)
    
    if current_overlap:
        suggestions.append(current_overlap)
    
    return suggestions

def get_user_confirmation(overlap_description, recommendations):
    """
    Ask user for confirmation before removing overlapping content.
    """
    print(f"\n📋 Overlap detected:")
    print(f"Description: {overlap_description}")
    print(f"Recommendations: {recommendations}")
    
    while True:
        response = input("\nShould we remove this overlap? (y/n/details): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        elif response == 'details':
            print(f"\nDetailed analysis:\n{recommendations}")
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'details' for more information.")

def remove_overlapping_chapters(notebook_path, headings_to_remove):
    """
    Remove specified chapters from a notebook and update chapter numbering.
    """
    print(f"✂️ Removing overlapping chapters from: {os.path.basename(notebook_path)}")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Sort cell indices in reverse order to avoid index shifting issues
    cells_to_remove = sorted(headings_to_remove, reverse=True)
    
    # Remove cells
    for cell_idx in cells_to_remove:
        if cell_idx < len(notebook['cells']):
            removed_content = ''.join(notebook['cells'][cell_idx]['source'])
            print(f"  🗑️ Removing cell {cell_idx}: {removed_content[:50]}...")
            del notebook['cells'][cell_idx]
    
    # Update chapter numbering
    notebook = update_chapter_numbering(notebook)
    
    # Save the modified notebook
    backup_path = notebook_path.replace('.ipynb', '_backup.ipynb')
    os.rename(notebook_path, backup_path)
    print(f"💾 Created backup: {os.path.basename(backup_path)}")
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated notebook saved: {os.path.basename(notebook_path)}")

def update_chapter_numbering(notebook):
    """
    Update chapter numbering in markdown cells (## format).
    """
    print("🔢 Updating chapter numbering...")
    
    chapter_counter = 1
    
    for cell in notebook['cells']:
        if cell['cell_type'] == 'markdown':
            content = ''.join(cell['source'])
            
            # Find and replace chapter numbers
            def replace_chapter_number(match):
                nonlocal chapter_counter
                heading_text = match.group(1).strip()
                # Remove existing numbers if present
                heading_text = re.sub(r'^\d+\.?\s*', '', heading_text)
                new_heading = f"## {chapter_counter}. {heading_text}"
                chapter_counter += 1
                return new_heading
            
            # Replace headings with updated numbering
            updated_content = re.sub(r'^##\s+(.+)$', replace_chapter_number, content, flags=re.MULTILINE)
            
            if updated_content != content:
                cell['source'] = [updated_content]
    
    print(f"✅ Updated numbering for {chapter_counter - 1} chapters")
    return notebook

def identify_overlapping_headings(all_notebook_headings, overlap_analysis):
    """
    Identify specific headings to remove based on overlap analysis.
    This function needs to be customized based on how ChatGPT formats its response.
    """
    # This is a placeholder implementation
    # You'll need to parse the ChatGPT response and match it to actual headings
    overlaps_to_remove = {}
    
    # For now, return empty dict - implement based on actual ChatGPT response format
    return overlaps_to_remove

def main():
    """Main function to run the notebook overlap management process."""
    print("🚀 Starting notebook overlap management...")
    
    # Initialize handlers
    drive_handler = GoogleDriveHandler(KEY_FILE, SCOPES)
    translator = TranslationHandler(OPENAI_API_KEY)
    
    all_notebook_headings = {}
    notebook_paths = {}
    
    # Download and extract headings from all notebooks
    for file_id in NOTEBOOK_FILE_IDS:
        try:
            # Download notebook
            file_path, file_name = download_notebook(drive_handler, file_id, DESTINATION_FOLDER)
            notebook_paths[file_id] = file_path
            
            # Extract headings
            headings = extract_headings_from_notebook(file_path)
            all_notebook_headings[file_path] = headings
            
        except Exception as e:
            print(f"❌ Error processing notebook {file_id}: {str(e)}")
            continue
    
    if len(all_notebook_headings) < 2:
        print("⚠️ Need at least 2 notebooks to compare for overlaps.")
        return
    
    # Analyze overlaps using ChatGPT
    overlap_analysis = compare_headings_with_chatgpt(translator, all_notebook_headings)
    
    if not overlap_analysis:
        print("❌ Could not analyze overlaps. Exiting.")
        return
    
    print("\n📊 Overlap Analysis Results:")
    print("=" * 50)
    print(overlap_analysis)
    print("=" * 50)
    
    # Parse suggestions (you may need to customize this based on ChatGPT's response format)
    suggestions = parse_overlap_suggestions(overlap_analysis)
    
    # Process each suggestion with user confirmation
    for suggestion in suggestions:
        if get_user_confirmation(suggestion['description'], suggestion['recommendations']):
            # Here you would implement the logic to identify and remove specific overlapping chapters
            # This requires parsing the ChatGPT response to identify specific headings and notebooks
            overlaps_to_remove = identify_overlapping_headings(all_notebook_headings, suggestion)
            
            for notebook_path, cell_indices in overlaps_to_remove.items():
                remove_overlapping_chapters(notebook_path, cell_indices)
        else:
            print("⏭️ Skipping this overlap...")
    
    print("\n🎉 Overlap management complete!")
    print("📁 Check the DESTINATION_FOLDER for updated notebooks")
    print("💾 Backup files were created with '_backup' suffix")

if __name__ == "__main__":
    main()