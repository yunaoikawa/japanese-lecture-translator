"""
Script to translate Jupyter notebook files from Google Drive using the Translator module.
This script allows specifying notebook file IDs directly.
"""

PROMPT_DOC_ID = "1UHefUKZlUDyxJJ76Wmx9Di0c9U6d67Ni3JB9ofZr1KU"  # Replace with your prompt document ID

import os
import sys
import json
import re
from time import sleep
from langdetect import detect

# Add current directory to path for importing myclasses
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from myclasses import (
    GoogleDriveHandler, TranslationHandler,
    KEY_FILE, SCOPES, OPENAI_API_KEY,
    DESTINATION_FOLDER, TRANSLATED_FOLDER
)

# List of notebook file IDs to process
# Add your notebook IDs here
NOTEBOOK_FILE_IDS = [
    #"1ooEwVOpGqf7YIlCgUCGyy14TdQrH4X4O",
    #"1ETG3nB589iloD8PlurtCtUNPb1mHJtgI",
    #"1aHBqz8Kp00uzMDoJQzQi7dF4yTWxEfx_",
    "1vW6h2n_et-Zu_u0CGiCL-x4O4SFyi2Eh",
    # Add more as needed
]

def download_notebook(drive_handler, file_id, destination_folder):
    """Download a notebook file from Google Drive."""
    # Get file metadata to determine the name
    file_metadata = drive_handler.service.files().get(fileId=file_id).execute()
    file_name = file_metadata['name']
    
    print(f"📥 Downloading notebook: {file_name}")
    
    # Use the download method from the drive handler
    request = drive_handler.service.files().get_media(fileId=file_id)
    os.makedirs(destination_folder, exist_ok=True)
    file_path = os.path.join(destination_folder, file_name)
    
    with open(file_path, 'wb') as f:
        downloader = drive_handler.service.files().get_media(fileId=file_id)
        f.write(downloader.execute())
    
    return file_path, file_name

def clean_code(text):
    """Remove any backticks from text that might cause Python issues."""
    # Replace backtick pairs that might be used for code highlighting in translation
    text = re.sub(r'```\w*\n', '', text)  # Remove opening code block markers
    text = re.sub(r'```', '', text)  # Remove closing code block markers
    text = re.sub(r'`([^`]*)`', r'\1', text)  # Remove inline code backticks
    text = re.sub(r'\*\*', '', text)
    text = text.rstrip('\n')
    return text

def chunk_text(text, max_chars=10000):
    """
    Splits text into chunks no larger than max_chars.
    Attempts to break at paragraph boundaries.
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def translate_large_text(translator, text, target_language, prompt_text):
    """
    Translate long text by breaking it into chunks and translating each separately.
    Preserves system messages and technical output.
    """

    # Store original for later comparison
    original_text = text
    
    # Chunk the text
    chunks = chunk_text(text)
    
    # If only one chunk, translate directly
    if len(chunks) == 1:
        try:
            #translated = translator.translate_text(text, target_language, prompt_text)
            translated = translator.translate_text(chunks[0], target_language, prompt_text)
            return translated
        except Exception as e:
            print(f"⚠️ Translation error (keeping original): {str(e)[:100]}...")
            return text
    
    # Multiple chunks need separate translation
    print(f"📏 Text too large, splitting into {len(chunks)} chunks for translation")
    translated_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"  🔤 Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        try:
            translated_chunk = translator.translate_text(chunk, target_language, prompt_text)
            translated_chunks.append(translated_chunk)
        except Exception as e:
            print(f"  ⚠️ Error translating chunk {i+1}: {str(e)[:100]}... (keeping original)")
            translated_chunks.append(chunk)  # Keep original if translation fails
    
    # Join the translated chunks
    return "\n\n".join(translated_chunks)

def contains_japanese(text):
    """Return True if the text contains any non-English (non-ASCII) characters."""
    return bool(re.search(r'[^\x00-\x7F]', text))


def translate_notebook(translator, file_path, prompt_text):
    """
    Translate ALL content in a Jupyter notebook.
    Translates markdown cells, code cells, and outputs.
    Handles large cells by chunking.
    Preserves Python system messages and warnings.
    """
    print(f"📖 Reading notebook: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    print("🌍 Translating notebook content...")
    
    # Process each cell in the notebook
    total_cells = len(notebook['cells'])
    for i, cell in enumerate(notebook['cells']):
        sleep(0.5)  # Avoid rate limits
        print(f"🔄 Processing cell {i+1}/{total_cells}...")
        
        # Translate markdown cells
        if cell['cell_type'] == 'markdown':
            print("  📝 Translating markdown cell...")
            markdown_content = ''.join(cell['source'])
            translated_markdown = translate_large_text(
                translator, 
                markdown_content, 
                target_language="English", 
                prompt_text=prompt_text
            )
            # Update the cell with translated content
            cell['source'] = [translated_markdown]
        
        elif cell['cell_type'] == 'code':
            print("  💻 Translating code cell...")
            code_content = ''.join(cell['source'])
            
            if contains_japanese(code_content):
                translated_code = translate_large_text(
                    translator,
                    code_content,
                    target_language="English",
                    prompt_text="This content is code. Translate Japanese comments, strings, and file names. Be extremely careful not to break the code functionality. Do not add any new lines, comments or change the code structure."
                )
                translated_code = clean_code(translated_code)
                cell['source'] = [translated_code]
            else:
                print("  🔍 No Japanese detected in code. Skipping translation.")
            
            if 'outputs' in cell:
                for output_idx, output in enumerate(cell['outputs']):
                    is_error = output.get('output_type') == 'error'

                    if 'text' in output and not is_error:
                        text_content = ''.join(output['text'])
                        if contains_japanese(text_content):
                            print(f"  📊 Translating output text ({len(text_content)} chars)...")
                            translated_text = translate_large_text(
                                translator,
                                text_content,
                                target_language="English",
                                prompt_text=prompt_text + "\nThis is likely code. Translate comments, strings, and docstrings ONLY. Keep all code syntax, variable names, function names, and logic identical. Be extremely careful not to break the code functionality."
                            )
                            output['text'] = [translated_text]
                        else:
                            print("  🔍 No Japanese detected in output text. Skipping translation.")

                    elif is_error:
                        print("  ⚠️ Error output detected - preserving without translation")

                    if 'data' in output:
                        if 'text/plain' in output['data']:
                            plain_text = ''.join(output['data']['text/plain'])
                            if contains_japanese(plain_text):
                                print(f"  📋 Translating plain text output ({len(plain_text)} chars)...")
                                translated_plain = translate_large_text(
                                    translator,
                                    plain_text,
                                    target_language="English",
                                    prompt_text=prompt_text + "\nThis is likely data output..."
                                )
                                output['data']['text/plain'] = [translated_plain]
                            else:
                                print("  🔍 No Japanese detected in plain text. Skipping translation.")

                        if 'text/html' in output['data']:
                            html_text = ''.join(output['data']['text/html'])
                            if contains_japanese(html_text):
                                print(f"  🌐 Translating HTML output ({len(html_text)} chars)...")
                                translated_html = translate_large_text(
                                    translator,
                                    html_text,
                                    target_language="English",
                                    prompt_text=prompt_text + "\nThis is HTML content..."
                                )
                                output['data']['text/html'] = [translated_html]
                            else:
                                print("  🔍 No Japanese detected in HTML. Skipping translation.")
    return notebook

def save_translated_notebook(notebook_data, original_name, translated_folder):
    """Save the translated notebook to the output folder."""
    os.makedirs(translated_folder, exist_ok=True)
    output_path = os.path.join(translated_folder, f"translated_{original_name}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(notebook_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved translated notebook to: {output_path}")
    return output_path

def main():
    """Main function to run the notebook translation process."""
    print("🚀 Starting notebook translation process...")
    
    # Initialize handlers
    drive_handler = GoogleDriveHandler(KEY_FILE, SCOPES)
    translator = TranslationHandler(OPENAI_API_KEY)
    
    # Get translation prompt
    prompt_text = drive_handler.get_prompt_from_doc(PROMPT_DOC_ID)
    print("✅ Loaded translation prompt.")
    
    # Process each notebook in the list
    for file_id in NOTEBOOK_FILE_IDS:
        try:
            # Download notebook
            file_path, file_name = download_notebook(drive_handler, file_id, DESTINATION_FOLDER)
            
            # Translate notebook
            translated_notebook = translate_notebook(translator, file_path, prompt_text)
            
            # Save translated notebook
            output_path = save_translated_notebook(
                translated_notebook, 
                file_name, 
                TRANSLATED_FOLDER
            )

        except Exception as e:
            print(f"❌ Error processing notebook {file_id}: {str(e)[:150]}...")
            print("⚠️ Continuing with next notebook...")
        
        if file_id != NOTEBOOK_FILE_IDS[-1]:  # Skip waiting after the last file
            print("⏱️ Waiting 2 hours before next file to avoid rate limits...")
    
    print("\n🎉 All notebooks translated.")

if __name__ == "__main__":
    main()