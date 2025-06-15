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
from dotenv import load_dotenv

#Environment variables
load_dotenv()

#API keys from .env file 
KEY_FILE = os.getenv("GOOGLE_KEY_FILE", "google_key.json")  # Path to your service account key file
SCOPES = ['https://www.googleapis.com/auth/drive']  # Google API scopes
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API
FOLDER_ID = os.getenv("GOOGLE_FOLDER_ID")  # ID of the folder containing files to translate
PROMPT_DOC_ID = os.getenv("GOOGLE_PROMPT_DOC_ID")  # ID of the Google Doc containing the translation prompt
DESTINATION_FOLDER = os.getenv("DESTINATION_FOLDER", "./GCI_copy_downloads")  # Local folder for downloaded files
TRANSLATED_FOLDER = os.getenv("TRANSLATED_FOLDER", "./GCI_copy_translated")  # Local folder for translated files

#Check if API key is set properly in .env file. Error if not. 
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required. Please set it in your .env file.")
if not FOLDER_ID:
    raise ValueError("GOOGLE_FOLDER_ID environment variable is required. Please set it in your .env file.")
if not PROMPT_DOC_ID:
    raise ValueError("GOOGLE_PROMPT_DOC_ID environment variable is required. Please set it in your .env file.")

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
    
    def test_folder_access(self, folder_id):
        """フォルダーにアクセスできるかの確認"""
        try:
            # Try to get the folder metadata
            folder_info = self.service.files().get(fileId=folder_id, fields="id, name, permissions").execute()
            print(f" Folder access successful!")
            print(f" Folder Name: {folder_info.get('name', 'Unknown')}")
            print(f" Folder ID: {folder_info.get('id')}")
            return True
        except Exception as e:
            print(f" Cannot access folder: {e}")
            return False
    
    def list_txt_files_in_folder(self, folder_id):
        """パスに設定されているフォルダ内にある .txtファイルとGoogle Docsのメタデータを取得"""
        query = f"'{folder_id}' in parents and (mimeType='text/plain' or mimeType='application/vnd.google-apps.document') and trashed=false"
        print(f" Debug: Searching with query: {query}")
        print(f" Debug: Folder ID: {folder_id}")
        results = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        print(f" Debug: Found {len(files)} files in folder")
        return files
    
    def get_doc_content(self, file_id):
        """Get content from a Google Doc file"""
        try:
            request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            return fh.getvalue().decode("utf-8")
        except Exception as e:
            print(f"Error reading Google Doc: {e}")
            return None
    
    def download_txt_file(self, file_id, file_name, destination_folder):
        """テキストファイルをダウンロード"""
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
    #Set delete_originals to True to delete the original files after translation.
    #Rate Limit などの問題に出会した場合、Wait_timeを変更してください
    def process_files(self, folder_id, prompt_doc_id, target_language="English", delete_originals=False, wait_time=0):
        """Process all text files and Google Docs in a folder, translate them, and optionally delete originals"""
        print(f" Testing access to folder: {folder_id}")
        if not self.drive_handler.test_folder_access(folder_id):
            print(" Cannot proceed - folder access failed!")
            return
            
        prompt_text = self.drive_handler.get_prompt_from_doc(prompt_doc_id)
        print("✅ Loaded translation prompt.")
        
        files = self.drive_handler.list_txt_files_in_folder(folder_id)
        print(f"📄 Found {len(files)} files in the folder.")
        
        for file in files:
            file_id = file['id']
            file_name = file['name']
            mime_type = file['mimeType']
            
            print(f"\n🔽 Processing: {file_name}...")
            
            # Handle Google Docs
            if mime_type == 'application/vnd.google-apps.document':
                print("📝 Reading Google Doc content...")
                content = self.drive_handler.get_doc_content(file_id)
                if not content:
                    print(f"❌ Failed to read Google Doc: {file_name}")
                    continue
            # Handle text files
            else:
                print("📄 Downloading text file...")
                file_path = self.drive_handler.download_txt_file(file_id, file_name, self.destination_folder)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            print(f"🌍 Translating content...")
            try:
                translated_text = self.translator.translate_text(content, target_language, prompt_text)
            except Exception as e:
                print(f"❌ Error translating {file_name}: {e}")
                continue
            
            output_path = os.path.join(self.translated_folder, "translated_" + file_name)
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write(translated_text)
            print(f"✅ Saved translated file to: {output_path}")
            
            if delete_originals:
                print(f"🗑️ Deleting original file from Drive: {file_name}")
                try:
                    self.drive_handler.delete_drive_file(file_id)
                except Exception as e:
                    print(f"⚠️ Could not delete file: {e}")
            else:
                print("🔒 Keeping original file in Drive.")
            
            # Wait to avoid rate limits
            if wait_time > 0:
                print(f"⏱️ Waiting {wait_time//60} minutes before next file...")
                time.sleep(wait_time)
        
        if delete_originals:
            print("\n🎉 All files translated and originals deleted.")
        else:
            print("\n🎉 All files translated. Originals kept in Drive.")