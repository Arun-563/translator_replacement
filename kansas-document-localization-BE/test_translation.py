#!/usr/bin/env python3
"""
Simple script to test Claude Sonnet integration for PDF translation.
"""

import sys
import os

# Add backend_code to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_code'))

from app.services.bedrock_service import BedrockService

def translate_text(spanish_text: str) -> str:
    """Translate Spanish text to English using Claude Sonnet."""
    
    bedrock = BedrockService()
    
    # Simple translation prompt
    system_prompt = "You are a professional translator. Translate the given Spanish text to English accurately. Preserve formatting and structure."
    
    user_prompt = f"Translate the following Spanish text to English:\n\n{spanish_text}"
    
    print("🔄 Translating with Claude Sonnet...")
    translated_text = bedrock.generate_text(system_prompt, user_prompt, max_tokens=2000)
    
    return translated_text


def main():
    print("=" * 60)
    print("Claude Sonnet Integration Test - Spanish to English")
    print("=" * 60)
    
    # Test 1: Simple Spanish text
    spanish_sample = """
    Hola, esto es un ejemplo de texto en español.
    La traducción automática es muy útil para procesar documentos multilingües.
    Esperamos que Claude Sonnet proporcione una traducción de alta calidad.
    """
    
    print("\n[TEST] Input Spanish text:")
    print(spanish_sample)
    
    try:
        result = translate_text(spanish_sample)
        print("\n[RESULT] Translated English text:")
        print(result)
        print("\n✓ Translation successful!")
        
    except Exception as e:
        print(f"\n✗ Translation failed: {e}")
        sys.exit(1)
    
    # Test 2: Get user input for custom translation
    print("\n" + "=" * 60)
    print("Want to translate custom text? (y/n)")
    choice = input("> ").strip().lower()
    
    if choice == 'y':
        print("\nEnter Spanish text (press Enter twice to finish):")
        lines = []
        empty_count = 0
        while empty_count < 1:
            line = input()
            if line == "":
                empty_count += 1
            else:
                lines.append(line)
                empty_count = 0
        
        custom_text = "\n".join(lines)
        
        if custom_text.strip():
            result = translate_text(custom_text)
            print("\n[RESULT] Translated text:")
            print(result)
        else:
            print("No text provided.")
    
    print("\n✓ Test completed!")


if __name__ == "__main__":
    main()
