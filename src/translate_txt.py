"""
Script to translate text files from Google Drive using the Translator module.
This script imports functionality from Translator.py.
"""

import os
import sys

# Add current directory to path for importing myclasses
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from myclasses import (
    TranslationManager, 
    KEY_FILE, SCOPES, OPENAI_API_KEY, 
    FOLDER_ID, PROMPT_DOC_ID, 
    DESTINATION_FOLDER, TRANSLATED_FOLDER
)

def main():
    """Main function to run the translation process"""
    # Create a TranslationManager instance with all necessary configurations
    translation_manager = TranslationManager(
        key_file=KEY_FILE,
        scopes=SCOPES,
        openai_api_key=OPENAI_API_KEY,
        destination_folder=DESTINATION_FOLDER,
        translated_folder=TRANSLATED_FOLDER
    )
    
    # Process all files in the specified Google Drive folder
    translation_manager.process_files(
        folder_id=FOLDER_ID,
        prompt_doc_id=PROMPT_DOC_ID,
        target_language="English",
        wait_time=0  # no wait time, Rate Limitに引っかかる場合は変更してください
    )

if __name__ == "__main__":
    main()