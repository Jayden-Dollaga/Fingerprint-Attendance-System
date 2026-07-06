# Read the file
with open('python/gui/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the corrupted line
content = content.replace(
    '        self.tabview.add("' + chr(65533) + ' Statistics")',
    '        self.tabview.add("📊 Statistics")'
)

# Write it back
with open('python/gui/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed the Statistics tab emoji!")
