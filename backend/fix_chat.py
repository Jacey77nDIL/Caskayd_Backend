# Fix chat.py to include file fields in MessageResponse

with open('chat.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix first occurrence (line 182-189)
content = content.replace(
    '''            models.MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender_type=msg.sender_type,
                sender_id=msg.sender_id,
                content=msg.content,
                created_at=msg.created_at,
                is_read=msg.is_read
            ) for msg in sorted(conversation.messages, key=lambda x: x.created_at)''',
    '''            models.MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender_type=msg.sender_type,
                sender_id=msg.sender_id,
                content=msg.content,
                file_url=msg.file_url,
                file_type=msg.file_type,
                created_at=msg.created_at,
                is_read=msg.is_read
            ) for msg in sorted(conversation.messages, key=lambda x: x.created_at)'''
)

# Fix second occurrence (line 247-255)
content = content.replace(
    '''        return models.MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_type=message.sender_type,
            sender_id=message.sender_id,
            content=message.content,
            created_at=message.created_at,
            is_read=message.is_read
        )''',
    '''        return models.MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_type=message.sender_type,
            sender_id=message.sender_id,
            content=message.content,
            file_url=message.file_url,
            file_type=message.file_type,
            created_at=message.created_at,
            is_read=message.is_read
        )'''
)

with open('chat.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated chat.py with file fields")
