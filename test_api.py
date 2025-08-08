# import requests
# import json
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Configuration
# API_BASE_URL = "http://localhost:8000"
# TEST_PDF_URL = "https://hackrx.blob.core.windows.net/assets/hackrx_6/policies/BAJHLIP23020V012223.pdf?sv=2023-01-03&st=2025-07-30T06%3A46%3A49Z&se=2025-09-01T06%3A46%3A00Z&sr=c&sp=rl&sig=9szykRKdGYj0BVm1skP%2BX8N9%2FRENEn2k7MQPUp33jyQ%3D"  # Replace with actual PDF URL
# AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")  # This must match API_AUTH_TOKEN in the .env


# def test_health_check():
#     """Test the health check endpoint"""
#     print("Testing health check...")
#     try:
#         response = requests.get(f"{API_BASE_URL}/health")
#         print(f"Health check status: {response.status_code}")
#         print(f"Response: {response.json()}")
#         return response.status_code == 200
#     except Exception as e:
#         print(f"Health check failed: {e}")
#         return False

# def test_main_endpoint():
#     """Test the main RAG endpoint using a remote URL (multipart/form-data)"""
#     print("\nTesting main RAG endpoint with remote PDF URL...")

#     questions = [
#         "What is the main topic of this document?",
#         "Do grandparents come under specific definiton family history?",
#         "Is gender change treatment covered?",
#         "What is code Excl?",
#         "Is there Grievance Redressal Procedure?"
#     ]

#     try:
#         # Construct multipart/form-data request
#         form_data = {
#             "document_url": TEST_PDF_URL,
#         }
#         files = []

#         # Add each question as a separate field
#         for question in questions:
#             files.append(("questions", (None, question)))

#         # Add document_url field
#         files.append(("document_url", (None, TEST_PDF_URL)))

#         response = requests.post(
#             f"{API_BASE_URL}/api/v1/hackrx/run",
#             files=files,
#             headers={
#                 "Authorization": f"Bearer {AUTH_TOKEN}",
#             },
#             timeout=300
#         )

#         print(f"Response status: {response.status_code}")
#         if response.status_code == 200:
#             result = response.json()
#             print("✅ Success! Answers received:\n")

#             for i, answer in enumerate(result["answers"], 1):
#                 print("=" * 80)
#                 print(f"🔍 Question {i}: {questions[i-1]}")
#                 print(f"\n💡 Answer:\n{answer}")
#         else:
#             print(f"❌ Error: {response.status_code}")
#             print(f"Response body: {response.text}")

#     except Exception as e:
#         print(f"❌ Request failed: {e}")


# def test_with_local_file():
#     """Test with a local PDF file"""
#     print("\nTesting with local file...")
    
#     # For local testing, you can use a local file path
#     local_test_payload = {
#         "documents": "./Test_Doc_2.pdf",  # Using your working PDF file
#         "questions": [
#             "Which gynaecological illnesses are covered?",
#         ]
#     }
    
#     try:
#         response = requests.post(
#             f"{API_BASE_URL}/api/v1/hackrx/run",
#             json=local_test_payload,
#             headers={"Content-Type": "application/json",
#                      "Authorization": f"Bearer {AUTH_TOKEN}"},
#             timeout=300
#         )
        
#         print(f"Local file test status: {response.status_code}")
#         if response.status_code == 200:
#             result = response.json()
#             print("✅ Local file test successful!")
#             print(f"Number of answers: {len(result['answers'])}")
            
#             # Print the actual answers
#             print("\n" + "="*80)
#             print("📋 DETAILED ANSWERS:")
#             print("="*80)
            
#             for i, answer in enumerate(result["answers"], 1):
#                 print(f"\n🔍 QUESTION {i}:")
#                 print(f"Question: {local_test_payload['questions'][i-1]}")
#                 print(f"\n💡 ANSWER:")
#                 print("-" * 50)
#                 print(answer)
#                 print("-" * 50)
                
#         else:
#             print(f"❌ Local file test failed: {response.text}")
            
#     except Exception as e:
#         print(f"❌ Local file test error: {e}")

# if __name__ == "__main__":
#     print("🚀 Starting API tests...")
    
#     # Test 1: Health check
#     if test_health_check():
#         print("✅ Health check passed")
#     else:
#         print("❌ Health check failed - make sure the server is running")
#         exit(1)
    
#     # Test 2: Main endpoint (you'll need to provide a valid PDF URL)
#     print(f"\n📝 Note: Update TEST_PDF_URL in this script with a real PDF URL")
#     print(f"Current TEST_PDF_URL: {TEST_PDF_URL}")
    
#     # Uncomment the line below when you have a valid PDF URL
#     test_main_endpoint()
    
#     # Test 3: Local file (if you have a local PDF)
#     # test_with_local_file()
    
#     print("\n🎉 Test script completed!")
#     print("\nTo run the actual tests:")
#     print("1. Make sure your FastAPI server is running: uvicorn main:app --reload")
#     print("2. Update the TEST_PDF_URL variable with a real PDF URL")
#     print("3. Uncomment the test_main_endpoint() call")
#     print("4. Run this script again: python test_api.py")

#######################################################################


#!/usr/bin/env python3
"""Simple test for your HackRX API"""

import requests
import json
import time

# Configuration
url = "http://localhost:8000/api/v1/hackrx/run"
token = "4e7ca5bcc342aa9a526573d4f483e19734697c969e6df3911a21b42a666c412e"

# Test data - FIXED: using 'documents' instead of 'document_url'
payload = {
    "documents": "https://hackrx.blob.core.windows.net/assets/hackrx_6/policies/CHOTGDP23004V012223.pdf?sv=2023-01-03&st=2025-07-30T06%3A46%3A49Z&se=2025-09-01T06%3A46%3A00Z&sr=c&sp=rl&sig=9szykRKdGYj0BVm1skP%2BX8N9%2FRENEn2k7MQPUp33jyQ%3D",
    "questions": [
        "What is this document about?",
        "What is a Qualified Nurse?"
    ]
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("🚀 Testing HackRX API...")
print(f"URL: {url}")
print(f"Questions: {len(payload['questions'])}")

try:
    start_time = time.time()
    
    # Make the request
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"⏱  Processing Time: {processing_time:.2f} seconds")
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        answers = result.get("answers", [])
        
        print(f"✅ Success! Received {len(answers)} answers")
        print("\n📝 Answers:")
        
        for i, answer in enumerate(answers, 1):
            print(f"\nQuestion {i}: {payload['questions'][i-1]}")
            print(f"Answer {i}: {answer}")
            print("-" * 50)
            
    else:
        print(f"❌ Error Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Is your server running?")
    print("   Try: python main.py")
    
except requests.exceptions.Timeout:
    print("⏰ Request timed out (>60 seconds)")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n🔍 Quick Debug:")
print("1. Check server is running: http://localhost:8000")
print("2. Check .env file has GOOGLE_API_KEY and API_AUTH_TOKEN")
print("3. Check token matches API_AUTH_TOKEN in .env")