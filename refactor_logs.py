import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # If structlog is not in the file, we can skip
    if 'structlog' not in content:
        return

    # Replace import structlog with from loguru import logger
    content = re.sub(r'^import structlog\n', 'from loguru import logger\n', content, flags=re.MULTILINE)
    
    # Remove logger = structlog.get_logger(__name__)
    content = re.sub(r'^logger\s*=\s*structlog\.get_logger\(__name__\)\n', '', content, flags=re.MULTILINE)

    # Now fix logger.info("msg", kw=arg) -> logger.bind(kw=arg).info("msg")
    # This regex looks for logger.(debug|info|warning|error)\( "message" , kwargs \)
    # We will iterate until no more changes happen (in case of nested structures, though unlikely)
    
    pattern = re.compile(r'logger\.(debug|info|warning|error)\s*\(\s*(["\'][^"\']+["\'])\s*,\s*([^)]+)\)')
    
    def replacer(match):
        level = match.group(1)
        msg = match.group(2)
        kwargs = match.group(3).strip()
        # if kwargs doesn't look like key=val, we might not want to touch it, but assuming it is:
        if '=' in kwargs:
            return f'logger.bind({kwargs}).{level}({msg})'
        return match.group(0) # don't touch if no kwargs or multiline complex stuff that regex misses

    new_content = pattern.sub(replacer, content)

    # Some multiline ones might be missed, but we can fix them manually or just rely on this for 90%
    if content != new_content or 'from loguru' in content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

app_dir = os.path.join('backend', 'app')
for root, _, files in os.walk(app_dir):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
