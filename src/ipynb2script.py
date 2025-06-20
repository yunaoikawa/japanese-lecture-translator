"""
Simple script to extract only markdown content from Jupyter notebook files.
Saves extracted content with original filename under data/scripts folder.
Supports Google Drive download.
Removes markdown formatting, bold text, images, titles, and other formatting.
"""

import os
import json
import sys
import argparse
import re
from pathlib import Path

OUTPUT_FOLDER = "data/scripts"  # Folder to save extracted content

# Optional Google Drive integration
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("📝 Google Drive integration not available. Install google-api-python-client for Google Drive support.")

# Google Drive configuration (if available)
KEY_FILE = os.getenv("GOOGLE_KEY_FILE", "google_key.json")
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveHandler:
    """Handles Google Drive integration for downloading files."""
    
    def __init__(self, key_file: str, scopes: list):
        """Initialize Google Drive service."""
        if not GOOGLE_DRIVE_AVAILABLE:
            raise ImportError("Google Drive libraries not available")
        
        if not os.path.exists(key_file):
            raise FileNotFoundError(f"Google service account key file not found: {key_file}")
        
        credentials = Credentials.from_service_account_file(key_file, scopes=scopes)
        self.service = build('drive', 'v3', credentials=credentials)
    
    def download_notebook(self, file_id: str, destination_folder: str = "data/downloads") -> str:
        """Download a notebook file from Google Drive."""
        try:
            # Get file metadata to determine the name
            file_metadata = self.service.files().get(fileId=file_id).execute()
            file_name = file_metadata['name']
            
            print(f"📥 Downloading notebook: {file_name}")
            
            # Create destination folder if it doesn't exist
            os.makedirs(destination_folder, exist_ok=True)
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            file_path = os.path.join(destination_folder, file_name)
            
            with open(file_path, 'wb') as f:
                f.write(request.execute())
            
            print(f"✅ Downloaded to: {file_path}")
            return file_path
            
        except Exception as e:
            raise Exception(f"Failed to download notebook from Google Drive: {str(e)}")

def extract_file_id_from_url(url: str) -> str:
    """Extract file ID from Google Drive URL."""
    # Handle different Google Drive URL formats
    if "/file/d/" in url:
        # Format: https://drive.google.com/file/d/FILE_ID/view
        return url.split("/file/d/")[1].split("/")[0]
    elif "id=" in url:
        # Format: https://drive.google.com/open?id=FILE_ID
        return url.split("id=")[1].split("&")[0]
    else:
        # Assume it's already a file ID
        return url.strip()

def clean_markdown_content(content: str) -> str:
    """Clean markdown content by removing formatting, images, titles, etc."""
    if not content.strip():
        return ""
    
    # Remove images (![alt text](url) format)
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    
    # Remove horizontal rules (--- or ***)
    content = re.sub(r'^[-*]{3,}$', '', content, flags=re.MULTILINE)
    
    # Remove titles and subtitles (# headers)
    content = re.sub(r'^#{1,6}\s+.*$', '', content, flags=re.MULTILINE)
    
    # Remove bold text formatting (***text*** or **text**)
    content = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', content)
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
    
    # Remove italic text formatting (*text*)
    content = re.sub(r'\*(.*?)\*', r'\1', content)
    
    # Remove inline code formatting (`code`)
    content = re.sub(r'`([^`]+)`', r'\1', content)
    
    # Remove code blocks (```code```)
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    
    # Remove links but keep the text [text](url) -> text
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    
    # Remove remaining standalone asterisks and stars
    content = re.sub(r'\*+', '', content)
    
    # Remove HTML tags if any
    content = re.sub(r'<[^>]+>', '', content)
    
    # Clean up excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Multiple empty lines to double
    content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single space

    # Remove markdown-style links like (http....)
    content = re.sub(r'\(http[^\)]*\)', '', content)

    # Remove markdown tables:
    # Remove lines that look like table headers or separators
    content = re.sub(r'^\|.*\|\s*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\|?[ \t\-:\|]+\|?\s*$', '', content, flags=re.MULTILINE)

    # Collapse multiple empty lines into one double newline
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

    # Collapse multiple spaces and tabs into a single space
    content = re.sub(r'[ \t]+', ' ', content)

    # Remove whatever is inside parentheses (e.g., (text))
    content = re.sub(r'\([^)]*\)', '', content)

    content = content.strip()
    
    return content

class SimpleNotebookExtractor:
    """Handles extraction of markdown content from Jupyter notebooks."""
    
    def load_notebook(self, file_path: str) -> dict:
        """Load a Jupyter notebook from file."""
        print(f"📖 Loading notebook: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
            return notebook
        except Exception as e:
            raise Exception(f"Failed to load notebook: {str(e)}")
    
    def extract_markdown_content(self, notebook: dict) -> list:
        """Extract all markdown cells from the notebook."""
        markdown_cells = []
        
        for i, cell in enumerate(notebook.get('cells', [])):
            if cell.get('cell_type') == 'markdown':
                content = ''.join(cell.get('source', []))
                if content.strip():  # Only include non-empty cells
                    # Clean the markdown content
                    cleaned_content = clean_markdown_content(content)
                    if cleaned_content.strip():  # Only add if there's content after cleaning
                        markdown_cells.append({
                            'cell_index': i,
                            'content': cleaned_content
                        })
            elif cell.get('cell_type') == 'code':
                # Add placeholder for code cells
                markdown_cells.append({
                    'cell_index': i,
                    'content': '\n\n\n\n\n',  # 5 new lines for code cells
                    'is_code_placeholder': True
                })
        
        return markdown_cells
    
    def format_content(self, markdown_cells: list) -> str:
        """Format extracted content into final output."""
        if not markdown_cells:
            return ""
        
        content_parts = []
        
        for cell in markdown_cells:
            if cell.get('is_code_placeholder'):
                # Just add the newlines for code cells
                content_parts.append(cell['content'])
            else:
                # Add cleaned markdown content
                content_parts.append(cell['content'])
        
        return ''.join(content_parts)
    
    def save_content(self, content: str, original_filename: str, folder: str = OUTPUT_FOLDER):
        """Save extracted content with original filename."""
        os.makedirs(folder, exist_ok=True)
        
        # Use original filename without extension, add .txt
        base_name = Path(original_filename).stem
        output_filename = f"{base_name}.txt"
        output_path = os.path.join(folder, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"💾 Saved content to: {output_path}")
        return output_path
    
    def process_notebook(self, notebook_path: str) -> dict:
        """Main processing function that extracts and saves markdown content."""
        # Load notebook
        notebook = self.load_notebook(notebook_path)
        
        # Extract markdown content
        print("📋 Extracting and cleaning markdown content...")
        markdown_cells = self.extract_markdown_content(notebook)
        
        markdown_count = sum(1 for cell in markdown_cells if not cell.get('is_code_placeholder'))
        code_count = sum(1 for cell in markdown_cells if cell.get('is_code_placeholder'))
        
        print(f"   Found {markdown_count} markdown cells (after cleaning)")
        print(f"   Found {code_count} code cells (replaced with newlines)")
        
        if not markdown_cells:
            print("⚠️ No content found in notebook")
            return {"status": "no_content"}
        
        # Format content
        formatted_content = self.format_content(markdown_cells)
        
        if not formatted_content.strip():
            print("⚠️ No extractable content found in notebook after cleaning")
            return {"status": "no_content"}
        
        # Save content with original filename
        original_filename = Path(notebook_path).name
        output_file = self.save_content(formatted_content, original_filename)
        
        return {
            "status": "success",
            "notebook": Path(notebook_path).stem,
            "markdown_cells": markdown_count,
            "code_cells": code_count,
            "output_file": output_file
        }

def download_notebook_from_drive(file_id_or_url: str, destination_folder: str = "data/downloads") -> str:
    """Download notebook from Google Drive if available."""
    if not GOOGLE_DRIVE_AVAILABLE:
        raise ImportError("Google Drive integration not available. Install google-api-python-client.")
    
    try:
        # Extract file ID from URL if needed
        file_id = extract_file_id_from_url(file_id_or_url)
        
        drive_handler = GoogleDriveHandler(KEY_FILE, SCOPES)
        return drive_handler.download_notebook(file_id, destination_folder)
    except Exception as e:
        raise Exception(f"Failed to download notebook: {str(e)}")

def main():
    """Main function to run the notebook content extraction."""
    parser = argparse.ArgumentParser(description="Extract and clean markdown content from Jupyter notebooks")
    parser.add_argument("notebook_path", nargs='?', help="Path to the Jupyter notebook file (or use --drive-url/--drive-file-id)")
    parser.add_argument("--drive-url", help="Google Drive URL to download and process")
    parser.add_argument("--drive-file-id", help="Google Drive file ID to download and process")
    parser.add_argument("--output-dir", help="Output directory for saved files", default=OUTPUT_FOLDER)
    parser.add_argument("--download-dir", help="Directory to download files from Google Drive", default="data/downloads")
    
    args = parser.parse_args()
    
    # Determine notebook path
    notebook_path = args.notebook_path
    
    # Handle Google Drive download if URL or file ID is provided
    if args.drive_url or args.drive_file_id:
        if not GOOGLE_DRIVE_AVAILABLE:
            print("❌ Google Drive integration not available. Install google-api-python-client.")
            return
        
        try:
            drive_input = args.drive_url or args.drive_file_id
            print(f"🔗 Downloading notebook from Google Drive...")
            notebook_path = download_notebook_from_drive(drive_input, args.download_dir)
        except Exception as e:
            print(f"❌ Failed to download from Google Drive: {str(e)}")
            return
    
    # Validate inputs
    if not notebook_path:
        print("❌ Either provide notebook_path, --drive-url, or --drive-file-id")
        return
        
    if not os.path.exists(notebook_path):
        print(f"❌ Notebook file not found: {notebook_path}")
        return
    
    if not notebook_path.endswith('.ipynb'):
        print("❌ File must be a .ipynb file")
        return
    
    try:
        # Initialize extractor
        extractor = SimpleNotebookExtractor()
        
        # Process notebook
        print(f"🚀 Processing notebook: {notebook_path}")
        result = extractor.process_notebook(notebook_path)
        
        # Print results
        if result["status"] == "success":
            print("\n✅ Processing completed successfully!")
            print(f"📊 Processed {result['markdown_cells']} markdown cells and {result['code_cells']} code cells")
            print(f"📄 Content saved to: {result['output_file']}")
            print("🧹 Removed: bold text, images, titles, horizontal rules, and other formatting")
        elif result["status"] == "no_content":
            print("⚠️ No extractable content found in the notebook")
        else:
            print(f"❌ Processing failed")
    
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")

def process_multiple_notebooks(directory_path: str):
    """Process all notebooks in a directory."""
    if not os.path.exists(directory_path):
        print(f"❌ Directory not found: {directory_path}")
        return
    
    extractor = SimpleNotebookExtractor()
    notebook_files = [f for f in os.listdir(directory_path) if f.endswith('.ipynb')]
    
    if not notebook_files:
        print(f"⚠️ No .ipynb files found in {directory_path}")
        return
    
    print(f"🔄 Processing {len(notebook_files)} notebooks from {directory_path}")
    
    for notebook_file in notebook_files:
        notebook_path = os.path.join(directory_path, notebook_file)
        print(f"\n📝 Processing: {notebook_file}")
        
        try:
            result = extractor.process_notebook(notebook_path)
            if result["status"] == "success":
                print(f"   ✅ Success: {result['markdown_cells']} markdown cells (cleaned)")
            else:
                print(f"   ⚠️ {result['status']}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python clean_notebook_extractor.py [notebook_path] [options]")
        print("\nThis script extracts markdown content and removes formatting like:")
        print("  • Bold text (**, ***)")
        print("  • Images (![alt](url))")
        print("  • Titles and headers (#)")
        print("  • Horizontal rules (---)")
        print("  • Links (keeps text only)")
        print("  • Code formatting (`code`)")
        print("\nOptions:")
        print("  --drive-url 'google_drive_url'      Download from Google Drive using full URL")
        print("  --drive-file-id 'file_id'           Download from Google Drive using file ID")
        print("  --output-dir 'output_folder'        Specify output directory (default: data/scripts)")
        print("  --download-dir 'download_folder'    Specify download directory for Google Drive files")
        print("\nExamples:")
        print("python clean_notebook_extractor.py my_notebook.ipynb")
        print("python clean_notebook_extractor.py --drive-url 'https://drive.google.com/file/d/1dwqt8Fx6cDZVt1zXT26tH4-t_ZqR-Qnb/view'")
        print("python clean_notebook_extractor.py --drive-file-id '1dwqt8Fx6cDZVt1zXT26tH4-t_ZqR-Qnb'")
        print("python clean_notebook_extractor.py notebooks/analysis.ipynb --output-dir extracted/")
        print("\nTo process multiple notebooks:")
        print("python -c \"from clean_notebook_extractor import process_multiple_notebooks; process_multiple_notebooks('notebooks/')\"")
    else:
        main()