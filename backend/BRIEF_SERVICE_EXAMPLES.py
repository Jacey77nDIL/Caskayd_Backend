"""
EXAMPLE USAGE: Brief & Cloudflare Service
Demonstrates all API endpoints and workflows
"""

# ============================================================
# EXAMPLE 1: Business Uploads a Brief
# ============================================================

"""
POST /api/briefs/upload
Content-Type: multipart/form-data

Body:
- file: (binary) campaign_brief.pdf

Response:
{
  "success": true,
  "public_url": "https://pub-caskayd-briefs.r2.dev/briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf",
  "object_key": "briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf",
  "file_name": "campaign_brief.pdf",
  "file_size": 2456789,
  "content_type": "application/pdf",
  "uploaded_at": "2025-02-17T14:52:30.123456",
  "message": "Brief uploaded successfully"
}
"""

import requests

def upload_brief(token: str, file_path: str):
    """Business uploads a brief file"""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.post(
            'http://localhost:8000/api/briefs/upload',
            headers=headers,
            files=files
        )
    
    return response.json()

# Usage
# result = upload_brief(token='your_business_token', file_path='brief.pdf')
# print(result['public_url'])  # https://pub-caskayd-briefs.r2.dev/...


# ============================================================
# EXAMPLE 2: Business Sends Brief as Message to Creator
# ============================================================

"""
POST /api/briefs/send/{conversation_id}
Content-Type: multipart/form-data

Params:
- conversation_id: 5
- message_text: "Please review this campaign brief for approval"

Body:
- file: (binary) campaign_brief.pdf

Response:
{
  "message_id": 42,
  "conversation_id": 5,
  "file_url": "https://pub-caskayd-briefs.r2.dev/briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf",
  "file_name": "campaign_brief.pdf",
  "file_type": "application/pdf",
  "content": "Please review this campaign brief for approval",
  "created_at": "2025-02-17T14:52:30.123456",
  "message": "Brief sent successfully as message"
}
"""

def send_brief_as_message(
    token: str,
    conversation_id: int,
    file_path: str,
    message_text: str = None
):
    """Business sends a brief as a message in a conversation"""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        headers = {'Authorization': f'Bearer {token}'}
        params = {}
        
        if message_text:
            params['message_text'] = message_text
        
        response = requests.post(
            f'http://localhost:8000/api/briefs/send/{conversation_id}',
            headers=headers,
            files=files,
            params=params
        )
    
    return response.json()

# Usage
# result = send_brief_as_message(
#     token='your_business_token',
#     conversation_id=5,
#     file_path='brief.pdf',
#     message_text='Review this campaign brief'
# )
# print(result['message_id'])  # 42
# print(result['file_url'])


# ============================================================
# EXAMPLE 3: Creator Downloads Brief from Message
# ============================================================

"""
GET /api/briefs/download/{message_id}

Response:
{
  "download_url": "https://{ACCOUNT_ID}.r2.cloudflarestorage.com/briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
  "expires_in_seconds": 3600,
  "file_name": "20250217_145230_a1b2c3d4_campaign_brief.pdf",
  "object_key": "briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf"
}

The download_url is a presigned URL that expires in 1 hour.
Use it to download the file directly from Cloudflare R2.
"""

def get_brief_download_url(token: str, message_id: int):
    """Creator gets presigned download URL for a brief"""
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(
        f'http://localhost:8000/api/briefs/download/{message_id}',
        headers=headers
    )
    
    return response.json()

# Usage
# result = get_brief_download_url(token='creator_token', message_id=42)
# download_url = result['download_url']
# 
# # Download the file
# file_response = requests.get(download_url)
# with open('downloaded_brief.pdf', 'wb') as f:
#     f.write(file_response.content)


# ============================================================
# EXAMPLE 4: Get Brief Metadata
# ============================================================

"""
GET /api/briefs/info/{message_id}

Response:
{
  "success": true,
  "file_name": "20250217_145230_a1b2c3d4_campaign_brief.pdf",
  "object_key": "briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf",
  "file_size": 2456789,
  "content_type": "application/pdf",
  "last_modified": "2025-02-17T14:52:30.123456",
  "etag": "\"a1b2c3d4e5f6g7h8\""
}
"""

def get_brief_info(token: str, message_id: int):
    """Get metadata about a brief"""
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(
        f'http://localhost:8000/api/briefs/info/{message_id}',
        headers=headers
    )
    
    return response.json()

# Usage
# info = get_brief_info(token='token', message_id=42)
# print(f"File size: {info['file_size']} bytes")
# print(f"Type: {info['content_type']}")
# print(f"Modified: {info['last_modified']}")


# ============================================================
# EXAMPLE 5: List All Briefs by Business
# ============================================================

"""
GET /api/briefs/list-my-briefs

Response:
[
  {
    "key": "briefs/business_1/20250217_145230_a1b2c3d4_campaign_brief.pdf",
    "size": 2456789,
    "last_modified": "2025-02-17T14:52:30.123456",
    "storage_class": "STANDARD"
  },
  {
    "key": "briefs/business_1/20250217_150000_e5f6g7h8_media_kit.pdf",
    "size": 1234567,
    "last_modified": "2025-02-17T15:00:00.123456",
    "storage_class": "STANDARD"
  }
]
"""

def list_business_briefs(token: str):
    """List all briefs uploaded by a business"""
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(
        'http://localhost:8000/api/briefs/list-my-briefs',
        headers=headers
    )
    
    return response.json()

# Usage
# briefs = list_business_briefs(token='business_token')
# for brief in briefs:
#     print(f"{brief['key']}: {brief['size']} bytes")


# ============================================================
# COMPLETE WORKFLOW EXAMPLE
# ============================================================

def complete_brief_workflow(
    business_token: str,
    creator_token: str,
    conversation_id: int,
    brief_file_path: str
):
    """
    Complete workflow from upload to download
    """
    
    # Step 1: Business sends brief as message
    print("1. Business sending brief as message...")
    message_result = send_brief_as_message(
        token=business_token,
        conversation_id=conversation_id,
        file_path=brief_file_path,
        message_text="Campaign brief for Q1 2025"
    )
    message_id = message_result['message_id']
    print(f"   Message created: {message_id}")
    
    # Step 2: Creator sees message and checks metadata
    print("2. Creator checking brief metadata...")
    metadata = get_brief_info(
        token=creator_token,
        message_id=message_id
    )
    print(f"   File size: {metadata['file_size']} bytes")
    print(f"   Type: {metadata['content_type']}")
    
    # Step 3: Creator gets download URL
    print("3. Creator getting download URL...")
    download_info = get_brief_download_url(
        token=creator_token,
        message_id=message_id
    )
    download_url = download_info['download_url']
    print(f"   Download URL expires in: {download_info['expires_in_seconds']}s")
    
    # Step 4: Creator downloads the file
    print("4. Creator downloading file...")
    file_response = requests.get(download_url)
    with open('downloaded_brief.pdf', 'wb') as f:
        f.write(file_response.content)
    print("   File downloaded successfully!")
    
    return {
        "message_id": message_id,
        "download_url": download_url,
        "file_size": metadata['file_size']
    }

# Usage:
# result = complete_brief_workflow(
#     business_token='business_token_here',
#     creator_token='creator_token_here',
#     conversation_id=5,
#     brief_file_path='campaign_brief.pdf'
# )


# ============================================================
# ERROR HANDLING EXAMPLES
# ============================================================

def handle_brief_errors(token: str, message_id: int):
    """
    Examples of error responses from the API
    """
    
    # Error 1: User not authenticated
    # Response: 401 Unauthorized
    response = requests.get(
        f'http://localhost:8000/api/briefs/info/{message_id}',
        headers={}  # Missing token
    )
    # response.status_code == 401
    
    # Error 2: User is not a business (trying to upload)
    # Response: 403 Forbidden
    # response.json() = {"detail": "Only businesses can upload briefs"}
    
    # Error 3: File too large (> 50MB)
    # Response: 400 Bad Request
    # response.json() = {"detail": "File validation failed: File size exceeds 50MB limit"}
    
    # Error 4: Invalid file type (e.g., .exe)
    # Response: 400 Bad Request
    # response.json() = {"detail": "File validation failed: File type '.exe' not allowed"}
    
    # Error 5: Message not found
    # Response: 404 Not Found
    # response.json() = {"detail": "Message not found"}
    
    # Error 6: Cloudflare service unavailable
    # Response: 503 Service Unavailable
    # response.json() = {"detail": "Cloudflare R2 service is not available"}


# ============================================================
# NOTES
# ============================================================

"""
1. AUTHENTICATION
   - All endpoints require a valid JWT token in the Authorization header
   - Format: Authorization: Bearer <token>
   - Get token by signing in as business or creator

2. FILE CONSTRAINTS
   - Max size: 50MB
   - Allowed types: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, XLSX, XLS, PPTX, PPT

3. PRESIGNED URLS
   - Download URLs expire after 1 hour
   - Can be regenerated by calling /download/{message_id} again

4. STORAGE
   - Files are stored in Cloudflare R2
   - Organized by business_id for easy retrieval
   - Archive prefix for deleted/archived files

5. SECURITY
   - Role-based: only businesses can upload
   - Access controlled: users can only access briefs in their conversations
   - File validated before upload
   - Unique names prevent overwrites
"""
