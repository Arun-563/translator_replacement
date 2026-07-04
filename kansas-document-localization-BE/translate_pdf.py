#!/usr/bin/env python3
"""
PDF Translation Script - Spanish to English
Translates PDF documents using Claude Sonnet via AWS Bedrock.
"""

import sys
import os
import json
from pathlib import Path

# Add backend_code to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_code'))

try:
    import PyPDF2
    pdf_available = True
except ImportError:
    pdf_available = False
    print("⚠️  PyPDF2 not installed. Will work with text files only.")
    print("   To process PDFs: pip install PyPDF2")

from app.services.bedrock_service import BedrockService
from app.prompts.translation_prompts import get_system_prompt, get_user_prompt


def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF file."""
    if not pdf_available:
        raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
    
    text = []
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num, page in enumerate(pdf_reader.pages):
            print(f"  Extracting page {page_num + 1}...", end="\r")
            page_text = page.extract_text()
            text.append(page_text)
    
    return "\n".join(text)


def translate_text(spanish_text: str, chunk_size: int = 3000, doc_type: str = "expense_reimbursement") -> str:
    """
    Translate Spanish text to English in chunks.
    Uses chunks to handle large texts and avoid token limits.
    
    Args:
        spanish_text: Text to translate
        chunk_size: Maximum characters per chunk
        doc_type: Type of document for optimized prompt (default: "expense_reimbursement")
    """
    bedrock = BedrockService()
    
    # Get optimized prompt for this document type
    system_prompt = get_system_prompt(doc_type)
    
    # Split text into chunks if needed
    if len(spanish_text) > chunk_size:
        print(f"  Text is large ({len(spanish_text)} chars). Translating in chunks...\n")
        chunks = []
        remaining = spanish_text
        
        while remaining:
            chunk = remaining[:chunk_size]
            
            # Try to break at a sentence boundary
            last_period = chunk.rfind('.')
            if last_period > chunk_size * 0.7:  # If period is in last 30%
                chunk = remaining[:last_period + 1]
            
            chunks.append(chunk)
            remaining = remaining[len(chunk):].lstrip()
        
        print(f"  Processing {len(chunks)} chunks...")
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"  Translating chunk {i + 1}/{len(chunks)}...", end="\r")
            user_prompt = get_user_prompt(chunk, doc_type)
            translated = bedrock.generate_text(system_prompt, user_prompt, max_tokens=4000)
            translated_chunks.append(translated)
        
        return "\n".join(translated_chunks)
    
    else:
        user_prompt = get_user_prompt(spanish_text, doc_type)
        return bedrock.generate_text(system_prompt, user_prompt, max_tokens=4000)


def save_translation(translated_text: str, output_path: str):
    """Save translated text to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(translated_text)
    print(f"✓ Translation saved to: {output_path}")


def main():
    print("\n" + "=" * 70)
    print("PDF Translation Tool - Spanish to English")
    print("=" * 70)
    
    # Define paths
    document_folder = Path(__file__).parent / "document"
    
    if not document_folder.exists():
        print(f"✗ Document folder not found: {document_folder}")
        print(f"  Creating folder...")
        document_folder.mkdir(exist_ok=True)
    
    # List files in document folder
    pdf_files = list(document_folder.glob("*.pdf"))
    txt_files = list(document_folder.glob("*.txt"))
    
    all_files = pdf_files + txt_files
    
    if not all_files:
        print(f"\n✗ No PDF or TXT files found in: {document_folder}")
        print(f"\nUsage:")
        print(f"  1. Place your Spanish PDF/TXT file in: {document_folder}/")
        print(f"  2. Run this script again")
        sys.exit(1)
    
    print(f"\n📁 Files found in {document_folder.name}/:")
    for i, file in enumerate(all_files, 1):
        print(f"  {i}. {file.name} ({file.stat().st_size} bytes)")
    
    # Select file
    if len(all_files) == 1:
        selected_file = all_files[0]
        print(f"\nSelected: {selected_file.name}")
    else:
        choice = input(f"\nSelect file number (1-{len(all_files)}): ").strip()
        try:
            selected_file = all_files[int(choice) - 1]
        except (ValueError, IndexError):
            print("✗ Invalid choice")
            sys.exit(1)
    
    print(f"\n🔄 Processing: {selected_file.name}")
    
    try:
        # Extract text
        if selected_file.suffix.lower() == ".pdf":
            if not pdf_available:
                print("✗ PyPDF2 not installed.")
                print("  Install with: pip install PyPDF2")
                sys.exit(1)
            print("  Extracting text from PDF...")
            text = extract_pdf_text(str(selected_file))
        else:  # .txt file
            print("  Reading text file...")
            with open(selected_file, 'r', encoding='utf-8') as f:
                text = f.read()
        
        print(f"  ✓ Extracted {len(text)} characters")
        
        # Translate (using expense_reimbursement prompt for this form)
        print("\n🔄 Translating with Claude Sonnet (Expense Reimbursement Form)...")
        translated = translate_text(text, doc_type="expense_reimbursement")
        
        print(f"  ✓ Translation complete ({len(translated)} characters)")
        
        # Save result
        output_path = document_folder / f"{selected_file.stem}_translated.txt"
        save_translation(translated, str(output_path))
        
        # Show preview
        print("\n📄 Preview of translation:")
        print("-" * 70)
        preview = translated[:500] + "..." if len(translated) > 500 else translated
        print(preview)
        print("-" * 70)
        
        print("\n✓ Translation completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
