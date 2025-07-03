#!/usr/bin/env python3
"""
This script generates flowing teaching narratives from Jupyter notebooks.
It creates a seamless explanation that adapts depth based on content complexity,
without any section markers or complexity labels.
"""

import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import time
from collections import deque
import re
import json
import tempfile
import shutil

# Constants
DEFAULT_CHUNK_TOKENS = 1500
MAX_CHUNK_TOKENS = 3000
TOKEN_ESTIMATE_DIVISOR = 4
MAX_RESPONSE_TOKENS = 4000
CONTEXT_WINDOW_CHARS = 800
RETRY_WAIT_MULTIPLIER = 5
RETRY_WAIT_EXPONENT = 2
RATE_LIMIT_WAIT_BUFFER = 0.1
MINUTE_IN_SECONDS = 60

try:
    import tiktoken
except ImportError:
    tiktoken = None

try:
    from openai import OpenAI, RateLimitError
except ImportError as e:
    raise ImportError("openai package is required. Install it via 'pip install openai>=1.3.0'") from e

# Optional Google Drive integration
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    logging.info("📝 Google Drive integration not available. Install google-api-python-client for Google Drive support.")

# Google Drive configuration (if available)
KEY_FILE = os.getenv("GOOGLE_KEY_FILE", "google_key.json")
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


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
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup if needed."""
        pass
    
    def download_notebook(self, file_id: str, destination_folder: str = "data/downloads") -> str:
        """Download a notebook file from Google Drive."""
        try:
            file_metadata = self.service.files().get(fileId=file_id).execute()
            file_name = file_metadata['name']
            
            logging.info(f"📥 Downloading notebook: {file_name}")
            
            os.makedirs(destination_folder, exist_ok=True)
            
            request = self.service.files().get_media(fileId=file_id)
            file_path = os.path.join(destination_folder, file_name)
            
            with tempfile.NamedTemporaryFile(mode='wb', dir=destination_folder, delete=False) as tmp_file:
                tmp_file.write(request.execute())
                temp_path = tmp_file.name
            
            shutil.move(temp_path, file_path)
            
            logging.info(f"✅ Downloaded to: {file_path}")
            return file_path
            
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Failed to download notebook from Google Drive: {str(e)}")


def extract_file_id_from_url(url: str) -> str:
    """Extract file ID from Google Drive URL."""
    if not url:
        return ""
    
    try:
        # Handle Colab URLs
        if "colab.research.google.com/drive/" in url:
            # Format: https://colab.research.google.com/drive/FILE_ID?usp=sharing
            parts = url.split("/drive/")
            if len(parts) > 1:
                file_id = parts[1].split("?")[0].split("#")[0]
                return file_id.strip()
        elif "/file/d/" in url:
            # Format: https://drive.google.com/file/d/FILE_ID/view
            parts = url.split("/file/d/")
            if len(parts) > 1:
                file_id_parts = parts[1].split("/")
                if file_id_parts:
                    return file_id_parts[0]
        elif "id=" in url:
            # Format: https://drive.google.com/open?id=FILE_ID
            parts = url.split("id=")
            if len(parts) > 1:
                file_id_parts = parts[1].split("&")
                if file_id_parts:
                    return file_id_parts[0]
    except Exception as e:
        logging.warning(f"Could not parse Google Drive URL: {e}")
    
    return url.strip()


def download_notebook_from_drive(file_id_or_url: str, destination_folder: str = "data/downloads") -> str:
    """Download notebook from Google Drive if available."""
    if not GOOGLE_DRIVE_AVAILABLE:
        raise ImportError("Google Drive integration not available. Install google-api-python-client.")
    
    try:
        file_id = extract_file_id_from_url(file_id_or_url)
        
        with GoogleDriveHandler(KEY_FILE, SCOPES) as drive_handler:
            return drive_handler.download_notebook(file_id, destination_folder)
    except Exception as e:
        raise Exception(f"Failed to download notebook: {str(e)}")


class TeachingScriptGenerator:
    """Generator for creating flowing teaching narratives from notebooks"""
    
    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
        rpm_limit: int = 20,
        tpm_limit: int = 40000,
    ):
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature
        self.max_chunk_tokens = min(max_chunk_tokens, MAX_CHUNK_TOKENS)
        
        # Rate limiting
        self._rpm_limit = rpm_limit
        self._tpm_limit = tpm_limit
        self._request_times = deque(maxlen=rpm_limit)
        self._token_events = deque()
        self._tokens_in_window = 0
        
        # Token encoder
        self._encoder = self._get_encoder()
        
    def _get_encoder(self):
        """Get appropriate token encoder"""
        if tiktoken is not None:
            try:
                return tiktoken.encoding_for_model(self.model)
            except (KeyError, Exception) as e:
                logging.debug(f"Could not get encoding for model {self.model}: {e}")
                return tiktoken.get_encoding("cl100k_base")
        return None
        
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        if not text:
            return 0
        if self._encoder:
            try:
                return len(self._encoder.encode(text))
            except Exception as e:
                logging.debug(f"Token encoding failed, using fallback: {e}")
        return max(1, len(text) // TOKEN_ESTIMATE_DIVISOR)
    
    def _extract_text_from_notebook(self, notebook_path: str) -> str:
        """Extract text content from a Jupyter notebook file with smart filtering"""
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in notebook file: {e}")
            raise ValueError(f"The file {notebook_path} is not a valid Jupyter notebook")
        except Exception as e:
            logging.error(f"Failed to read notebook file: {e}")
            raise
        
        content_parts = []
        
        for cell in notebook.get('cells', []):
            cell_type = cell.get('cell_type', '')
            source = cell.get('source', [])
            
            # Handle both list and string formats
            if isinstance(source, str):
                source = source
            else:
                source = ''.join(source)
            
            if not source.strip():
                continue
            
            # Skip cells that are just large data (base64 images, etc.)
            if 'data:image' in source and len(source) > 10000:
                # Replace large embedded images with a placeholder
                content_parts.append("[Image content omitted]")
                continue
            
            if cell_type == 'markdown':
                # Clean up markdown but keep structure
                cleaned = self._clean_markdown_lightly(source.strip())
                if cleaned:
                    content_parts.append(cleaned)
            elif cell_type == 'code':
                # Include code with markers for context
                code_content = f"```python\n{source.strip()}\n```"
                content_parts.append(code_content)
                
                # Add outputs if they're meaningful (not too large)
                if 'outputs' in cell:
                    output_text = self._extract_cell_output(cell['outputs'])
                    if output_text:
                        content_parts.append(f"Output:\n{output_text}")
        
        # Join with double newlines for natural separation
        return '\n\n'.join(content_parts)
    
    def _clean_markdown_lightly(self, text: str) -> str:
        """Light cleaning of markdown while preserving structure"""
        # Remove horizontal rules
        text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # But keep headers for context (they help understand structure)
        # Keep lists, links, and other formatting that aids comprehension
        
        return text.strip()
    
    def _extract_cell_output(self, outputs: List[Dict]) -> str:
        """Extract meaningful output from cell outputs"""
        output_parts = []
        
        for output in outputs[:3]:  # Limit to first 3 outputs
            if output.get('output_type') == 'stream':
                text = ''.join(output.get('text', []))
                if text and len(text) < 500:  # Only include small outputs
                    output_parts.append(text.strip())
            elif output.get('output_type') == 'execute_result':
                data = output.get('data', {})
                if 'text/plain' in data:
                    text = ''.join(data['text/plain'])
                    if text and len(text) < 500:
                        output_parts.append(text.strip())
        
        return '\n'.join(output_parts)
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into manageable chunks based on natural breaks and token limits"""
        chunks = []
        
        # First split by major sections (headers)
        sections = re.split(r'\n(?=#\s)', text)
        
        current_chunk = []
        current_tokens = 0
        
        for section in sections:
            section_tokens = self.estimate_tokens(section)
            
            # If a single section is too large, split it further
            if section_tokens > self.max_chunk_tokens:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split large section by paragraphs or code blocks
                paragraphs = re.split(r'\n\n+', section)
                
                for para in paragraphs:
                    para_tokens = self.estimate_tokens(para)
                    
                    if current_tokens + para_tokens > self.max_chunk_tokens and current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = [para]
                        current_tokens = para_tokens
                    else:
                        current_chunk.append(para)
                        current_tokens += para_tokens
            
            # Section fits within limits
            elif current_tokens + section_tokens > self.max_chunk_tokens and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [section]
                current_tokens = section_tokens
            else:
                # Add to current chunk
                current_chunk.append(section)
                current_tokens += section_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _respect_rate_limits(self, estimated_tokens: int):
        """Respect both RPM and TPM limits"""
        now = time.time()
        
        # Clean old events
        while self._request_times and now - self._request_times[0] >= MINUTE_IN_SECONDS:
            self._request_times.popleft()
            
        while self._token_events and now - self._token_events[0][0] >= MINUTE_IN_SECONDS:
            _, tokens = self._token_events.popleft()
            self._tokens_in_window -= tokens
            
        # Check RPM
        if len(self._request_times) >= self._rpm_limit:
            wait_time = MINUTE_IN_SECONDS - (now - self._request_times[0]) + RATE_LIMIT_WAIT_BUFFER
            logging.info(f"RPM limit reached. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            
        # Check TPM
        if self._tokens_in_window + estimated_tokens > self._tpm_limit:
            if self._token_events:
                wait_time = MINUTE_IN_SECONDS - (now - self._token_events[0][0]) + RATE_LIMIT_WAIT_BUFFER
                logging.info(f"TPM limit reached. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                # Clean up old events and try again
                now = time.time()
                while self._token_events and now - self._token_events[0][0] >= MINUTE_IN_SECONDS:
                    _, tokens = self._token_events.popleft()
                    self._tokens_in_window -= tokens
                
        # Record request
        self._request_times.append(now)
        self._token_events.append((now, estimated_tokens))
        self._tokens_in_window += estimated_tokens
    
    def _call_openai(self, messages: List[dict], max_retries: int = 3) -> str:
        """Call OpenAI API with retry logic"""
        if not messages:
            raise ValueError("Messages cannot be empty")
        
        estimated_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        
        for attempt in range(max_retries):
            self._respect_rate_limits(estimated_tokens)
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=MAX_RESPONSE_TOKENS,
                )
                return response.choices[0].message.content.strip()
                
            except RateLimitError:
                wait_time = RETRY_WAIT_MULTIPLIER * (RETRY_WAIT_EXPONENT ** attempt)
                logging.warning(f"Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"API call failed: {e}")
                if attempt == max_retries - 1:
                    raise
                    
        raise RuntimeError("Max retries exceeded")
    
    def _generate_teaching_script_for_chunk(
        self, 
        chunk: str, 
        chunk_index: int,
        total_chunks: int,
        previous_context: str = "",
        is_first: bool = False,
        is_final: bool = False
    ) -> str:
        """Generate teaching script for a single chunk"""
        
        # Adjust the prompt based on position
        position_guidance = ""
        if is_first:
            position_guidance = "You're beginning the lesson. Provide a natural introduction that sets the context."
        elif is_final:
            position_guidance = "You're concluding the lesson. Wrap up naturally, reinforcing key takeaways."
        else:
            position_guidance = f"Continue the explanation naturally from where we left off."
        
        messages = [
            {
                "role": "system",
                "content": f"""You are creating a teaching script that will be read aloud for a video lecture.

CRITICAL INSTRUCTIONS:
1. Write ONLY the teaching narrative - pure spoken words
2. NO section headers, NO labels, NO formatting markers
3. Create a natural, flowing explanation that could be read aloud seamlessly
4. For simple concepts: provide brief, clear explanations
5. For complex concepts: go into more depth with examples and clarification
6. Maintain conversational yet professional tone
7. {position_guidance}

The students have basic programming knowledge but may need help with advanced concepts.
Focus on clarity and natural transitions."""
            }
        ]
        
        if previous_context and not is_first:
            messages.append({
                "role": "system",
                "content": f"Continue naturally from this context: ...{previous_context}"
            })
        
        messages.append({
            "role": "user",
            "content": f"""Create a flowing teaching narrative for this content:

{chunk}

Remember: Write ONLY the words to be spoken. No formatting, no sections, just natural teaching narrative."""
        })
        
        return self._call_openai(messages)
    
    def _create_smooth_transitions(self, scripts: List[str]) -> str:
        """Ensure smooth transitions between script segments"""
        if len(scripts) <= 1:
            return '\n\n'.join(scripts)
        
        # Join with natural paragraph breaks
        combined = []
        
        for i, script in enumerate(scripts):
            # Remove any potential leading/trailing whitespace
            script = script.strip()
            
            # Check if this segment starts abruptly (might need smoothing)
            if i > 0 and not script[0].islower() and not any(script.startswith(phrase) for phrase in 
                ['Now', 'Next', 'Let\'s', 'Moving', 'So', 'This', 'Here', 'In']):
                # This might be an abrupt start, but we'll trust the AI's flow
                pass
            
            combined.append(script)
        
        return '\n\n'.join(combined)
    
    def process_file(self, file_path: str, output_dir: str = "data/teaching_scripts") -> str:
        """Process a notebook or text file to generate teaching script"""
        # Validate input
        if not file_path:
            raise ValueError("file_path cannot be empty")
        
        try:
            file_path = Path(file_path)
        except Exception as e:
            raise ValueError(f"Invalid file path: {e}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine file type and extract content
        if file_path.suffix.lower() == '.ipynb':
            logging.info(f"Processing notebook file: {file_path}")
            content = self._extract_text_from_notebook(str(file_path))
        elif file_path.suffix.lower() in ['.txt', '.md']:
            logging.info(f"Processing text file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}. Supported: .ipynb, .txt, .md")
        
        # Split into chunks
        chunks = self._split_into_chunks(content)
        logging.info(f"Split content into {len(chunks)} chunks")
        
        # Generate teaching scripts for each chunk
        script_parts = []
        previous_context = ""
        
        for i, chunk in enumerate(chunks):
            chunk_tokens = self.estimate_tokens(chunk)
            logging.info(f"Processing chunk {i+1}/{len(chunks)} (~{chunk_tokens} tokens)")
            
            is_first = i == 0
            is_final = i == len(chunks) - 1
            
            script = self._generate_teaching_script_for_chunk(
                chunk, 
                i,
                len(chunks),
                previous_context,
                is_first,
                is_final
            )
            
            script_parts.append(script)
            
            # Update context for next chunk (last portion of current script)
            if len(script) > 100:
                previous_context = script[-CONTEXT_WINDOW_CHARS:]
            
            logging.info(f"  Generated {len(script)} characters")
        
        # Combine all parts with smooth transitions
        final_script = self._create_smooth_transitions(script_parts)
        
        # Save the output
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_file = Path(output_dir) / f"{file_path.stem}_teaching_script.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_script)
        
        logging.info(f"✅ Teaching script saved to: {output_file}")
        logging.info(f"📊 Total length: {len(final_script)} characters")
        
        return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Generate flowing teaching narratives from Jupyter notebooks"
    )
    parser.add_argument("file_path", nargs='?', help="Path to .ipynb notebook or .txt/.md text file")
    parser.add_argument("--drive-url", help="Google Drive URL to download and process")
    parser.add_argument("--drive-file-id", help="Google Drive file ID to download and process")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use")
    parser.add_argument("--temperature", type=float, default=0.7, help="Generation temperature")
    parser.add_argument("--output-dir", default="data/teaching_scripts", help="Output directory")
    parser.add_argument("--download-dir", default="data/downloads", help="Directory for Google Drive downloads")
    parser.add_argument("--max-chunk-tokens", type=int, default=DEFAULT_CHUNK_TOKENS, 
                       help="Maximum tokens per chunk")
    parser.add_argument("--rpm-limit", type=int, default=20, help="Requests per minute limit")
    parser.add_argument("--tpm-limit", type=int, default=40000, help="Tokens per minute limit")
    
    args = parser.parse_args()
    
    # Determine file path
    file_path = args.file_path
    
    # Handle Google Drive download if URL or file ID is provided
    if args.drive_url or args.drive_file_id:
        if not GOOGLE_DRIVE_AVAILABLE:
            logging.error("❌ Google Drive integration not available. Install google-api-python-client.")
            return
        
        try:
            drive_input = args.drive_url or args.drive_file_id
            logging.info(f"🔗 Downloading notebook from Google Drive...")
            file_path = download_notebook_from_drive(drive_input, args.download_dir)
        except Exception as e:
            logging.error(f"❌ Failed to download from Google Drive: {str(e)}")
            return
    
    # Validate inputs
    if not file_path:
        logging.error("❌ Either provide file_path, --drive-url, or --drive-file-id")
        return
    
    # Process the file
    try:
        generator = TeachingScriptGenerator(
            model=args.model,
            temperature=args.temperature,
            max_chunk_tokens=args.max_chunk_tokens,
            rpm_limit=args.rpm_limit,
            tpm_limit=args.tpm_limit,
        )
        
        generator.process_file(file_path, args.output_dir)
        
    except FileNotFoundError as e:
        logging.error(f"❌ {e}")
        return
    except ValueError as e:
        logging.error(f"❌ {e}")
        return
    except Exception as e:
        logging.error(f"Failed to process file: {e}")
        raise


if __name__ == "__main__":
    main()