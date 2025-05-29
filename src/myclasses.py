"""
Translator module that provides classes for translation functionality.
Can be imported and used by other Python scripts.
"""

import io
import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import openai

# Configuration constants
KEY_FILE = "google_key.json"  # Path to your service account key file
SCOPES = ['https://www.googleapis.com/auth/drive']  # Google API scopes
OPENAI_API_KEY = ""  # Your OpenAI API key
FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID"  # ID of the folder containing files to translate
PROMPT_DOC_ID = "YOUR_PROMPT_DOC_ID"  # ID of the Google Doc containing the translation prompt
DESTINATION_FOLDER = "./GCI_copy_downloads"  # Local folder for downloaded files
TRANSLATED_FOLDER = "./GCI_copy_translated"  # Local folder for translated files

class GoogleDriveHandler:
    """Class to handle Google Drive operations"""
    
    def __init__(self, key_file, scopes):
        """Initialize with credentials"""
        self.credentials = service_account.Credentials.from_service_account_file(key_file, scopes=scopes)
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def get_prompt_from_doc(self, file_id):
        """Download and return the prompt text from a Google Doc."""
        request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return fh.getvalue().decode("utf-8")
    
    def list_txt_files_in_folder(self, folder_id):
        """Return list of .txt file metadata in a Google Drive folder."""
        query = f"'{folder_id}' in parents and mimeType='text/plain' and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        return results.get('files', [])
    
    def download_txt_file(self, file_id, file_name, destination_folder):
        """Download a .txt file from Google Drive to local folder."""
        os.makedirs(destination_folder, exist_ok=True)
        request = self.service.files().get_media(fileId=file_id)
        file_path = os.path.join(destination_folder, file_name)
        with io.FileIO(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        return file_path
    
    def delete_drive_file(self, file_id):
        """Move a file in Google Drive to trash."""
        self.service.files().update(fileId=file_id, body={'trashed': True}).execute()


class TranslationHandler:
    """Class to handle translation operations"""
    
    def __init__(self, api_key):
        """Initialize with OpenAI API key"""
        self.api_key = api_key
        openai.api_key = api_key

    @staticmethod
    def retry_with_backoff(func, *args, retries=3, delay=3, **kwargs):
        """
        Retry a function up to `retries` times with a fixed `delay` between attempts.
        Specifically useful for handling rate limit errors.
        """
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    print(f"⏳ Rate limit hit, retrying in {delay} seconds... ({attempt+1}/{retries})")
                    time.sleep(delay)
                else:
                    raise e
        raise RuntimeError(f"Failed after {retries} retries due to rate limits.")
    
    def translate_text(self, content, target_language, prompt_text):
        """Translate content using OpenAI API with prompt."""
        def call_openai():
            return openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": content}
                ]
            )
        
        response = self.retry_with_backoff(call_openai)
        return response.choices[0].message.content.strip()

    
    def translate_file(self, file_path, target_language, prompt_text):
        """Read file and return its translated content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.translate_text(content, target_language, prompt_text)

class TranslationManager:
    """High-level class that manages the entire translation workflow"""
    
    def __init__(self, key_file, scopes, openai_api_key, destination_folder, translated_folder):
        """Initialize all components needed for translation workflow"""
        self.drive_handler = GoogleDriveHandler(key_file, scopes)
        self.translator = TranslationHandler(openai_api_key)
        self.destination_folder = destination_folder
        self.translated_folder = translated_folder
        os.makedirs(self.destination_folder, exist_ok=True)
        os.makedirs(self.translated_folder, exist_ok=True)
    
    def process_files(self, folder_id, prompt_doc_id, target_language="English", wait_time=7200):
        """Process all text files in a folder, translate them, and optionally delete originals"""
        prompt_text = self.drive_handler.get_prompt_from_doc(prompt_doc_id)
        print("✅ Loaded translation prompt.")
        
        txt_files = self.drive_handler.list_txt_files_in_folder(folder_id)
        print(f"📄 Found {len(txt_files)} .txt files in the folder.")
        
        for file in txt_files:
            file_id = file['id']
            file_name = file['name']
            print(f"\n🔽 Downloading: {file_name}...")
            file_path = self.drive_handler.download_txt_file(file_id, file_name, self.destination_folder)
            
            print(f"🌍 Translating file {file_name}...")
            try:
                translated_text = self.translator.translate_file(file_path, target_language, prompt_text)
            except Exception as e:
                print(f"❌ Error translating {file_name}: {e}")
                continue
            
            output_path = os.path.join(self.translated_folder, "translated_" + file_name)
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write(translated_text)
            print(f"✅ Saved translated file to: {output_path}")
            
            print(f"🗑️ Deleting original file from Drive: {file_name}")
            self.drive_handler.delete_drive_file(file_id)
            
            # Wait to avoid rate limits
            if wait_time > 0:
                print(f"⏱️ Waiting {wait_time//60} minutes before next file...")
                sleep(wait_time)
        
        print("\n🎉 All files translated and originals deleted.")