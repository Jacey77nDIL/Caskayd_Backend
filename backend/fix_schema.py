import re

# Read the file
with open('schemas.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the MessageResponse class
old_pattern = r'class MessageResponse\(BaseModel\):\s+id: int\s+conversation_id: int\s+sender_type: str\s+sender_id: int\s+content: str\s+created_at: datetime\s+is_read: bool'

new_class = '''class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_type: str
    sender_id: int
    content: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    created_at: datetime
    is_read: bool'''

content = re.sub(old_pattern, new_class, content)

# Write back
with open('schemas.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated MessageResponse schema")
