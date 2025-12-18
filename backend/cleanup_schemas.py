import re

with open('schemas.py', 'r') as f:
    content = f.read()

# Remove all PresignedUrlRequest class definitions
content = re.sub(r'\nclass PresignedUrlRequest\(BaseModel\):\s*\n\s*file_name: str\s*\n\s*file_type: str\s*\n\s*', '\n', content)

with open('schemas.py', 'w') as f:
    f.write(content)
    
print('Done - PresignedUrlRequest removed from schemas.py')
