import boto3
import json

# ✅ Use your profile
session = boto3.Session(profile_name="temp-creds-tttt4")

client = session.client(
    "bedrock-runtime",
    region_name="us-east-1"
)

try:
    response = client.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello Bedrock"}
                    ]
                }
            ]
        })
    )

    raw_response = response["body"].read().decode("utf-8")

    print("✅ RAW RESPONSE:\n", raw_response)

except Exception as e:
    print("❌ ERROR OCCURRED:")
    print(e)