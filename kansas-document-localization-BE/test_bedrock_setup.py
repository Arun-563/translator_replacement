#!/usr/bin/env python3
"""
Test script to verify AWS Bedrock setup is complete.
Run this from the backend_code directory.
"""

import os
import sys
import json

# Add backend_code to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_code'))

try:
    import boto3
    print("✓ boto3 installed")
except ImportError:
    print("✗ boto3 not installed. Run: pip install boto3")
    sys.exit(1)

# Test 1: Verify credentials
print("\n[TEST 1] Verifying AWS credentials...")
try:
    profile = os.getenv("AWS_PROFILE", "temp-creds-tttt4")
    region = os.getenv("AWS_REGION", "ap-south-1")
    
    session = boto3.Session(profile_name=profile, region_name=region)
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    print(f"✓ Credentials valid")
    print(f"  Account: {identity['Account']}")
    print(f"  ARN: {identity['Arn']}")
except Exception as e:
    print(f"✗ Credentials failed: {e}")
    sys.exit(1)

# Test 2: Verify Bedrock service access
print("\n[TEST 2] Checking Bedrock service availability...")
try:
    bedrock = session.client("bedrock", region_name=region)
    models = bedrock.list_foundation_models()
    print(f"✓ Bedrock service accessible")
    print(f"  Models available: {len(models.get('modelSummaries', []))}")
except Exception as e:
    print(f"✗ Bedrock service failed: {e}")
    print(f"  (Make sure Bedrock is enabled in your region: {region})")
    sys.exit(1)

# Test 3: List available models and inference profiles
print("\n[TEST 3] Listing available models...")
try:
    bedrock = session.client("bedrock", region_name=region)
    models = bedrock.list_foundation_models()
    
    print(f"  Available models ({len(models['modelSummaries'])}):")
    for model in models['modelSummaries'][:5]:
        print(f"    - {model['modelId']}")
    
    # Check for inference profiles
    try:
        profiles = bedrock.list_inference_profiles()
        print(f"\n  Available inference profiles ({len(profiles.get('inferenceProfileSummaries', []))}):")
        for profile in profiles.get('inferenceProfileSummaries', [])[:3]:
            print(f"    - {profile['inferenceProfileName']} ({profile.get('inferenceProfileArn', 'N/A')})")
    except Exception as e:
        print(f"  (No inference profiles found: {e})")

except Exception as e:
    print(f"✗ Model listing failed: {e}")
    sys.exit(1)

# Test 4: Try to invoke a model
print("\n[TEST 4] Testing model invocation...")
try:
    bedrock_runtime = session.client("bedrock-runtime", region_name=region)
    
    # Use the inference profile ARN
    model_id = "arn:aws:bedrock:ap-south-1:269336772098:inference-profile/apac.anthropic.claude-3-5-sonnet-20240620-v1:0"
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "system": "You are a helpful assistant.",
        "messages": [
            {
                "role": "user",
                "content": "Say 'Bedrock is working!' and nothing else."
            }
        ]
    }
    
    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )
    
    response_body = json.loads(response["body"].read())
    result = response_body["content"][0]["text"]
    
    print(f"✓ Model invocation successful!")
    print(f"  Model: {model_id}")
    print(f"  Response: {result.strip()}")
    
except Exception as e:
    error_msg = str(e)
    print(f"✗ Model invocation failed: {e}")
    
    if "inference profile" in error_msg.lower():
        print(f"\n  → Need to use inference profile instead:")
        print(f"    1. Go to AWS Bedrock Console → Inference profiles")
        print(f"    2. Create a new inference profile with Claude Sonnet")
        print(f"    3. Use the profile ARN in bedrock_service.py")
    elif "access" in error_msg.lower() or "denied" in error_msg.lower():
        print(f"  → Add IAM permission: bedrock:InvokeModel")
    else:
        print(f"  → Check model availability in region {region}")
    sys.exit(1)

print("\n" + "="*50)
print("✓ ALL TESTS PASSED - Bedrock is fully set up!")
print("="*50)
