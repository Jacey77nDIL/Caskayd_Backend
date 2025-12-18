#!/usr/bin/env python
lines = open('schemas.py').readlines()
new_lines = []
skip_next = 0
for i, line in enumerate(lines):
    if 'class PresignedUrlRequest' in line:
        skip_next = 4  # Skip class line + 3 content lines + 1 blank
        continue
    if skip_next > 0:
        skip_next -= 1
        continue
    new_lines.append(line)

with open('schemas.py', 'w') as f:
    f.writelines(new_lines)
print('Removed PresignedUrlRequest classes')
