#!/usr/bin/env python3
# UserPromptSubmit 훅 스크립트
# stdin으로 들어오는 JSON에서 prompt를 추출하여 history.prompt.txt에 저장

import sys
import json
import re
import os

# stdin을 UTF-8로 읽어 한글 깨짐 방지
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

data = json.load(sys.stdin)
prompt = data.get('prompt', '')

if not prompt:
    sys.exit(0)

file_path = 'history.prompt.txt'

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = f.read().splitlines()
else:
    lines = []

# 현재 가장 큰 번호 찾기 (없으면 0)
max_num = 0
for line in lines:
    m = re.match(r'^(\d+)\s', line)
    if m:
        n = int(m.group(1))
        if n > max_num:
            max_num = n

num = max_num + 1

# 새 항목을 맨 앞에 추가 (빈 줄 포함)
new_lines = [f'{num} {prompt}', ''] + lines

with open(file_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines) + '\n')
