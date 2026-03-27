import UnityPy


def parse_bundle(data: bytes) -> tuple[str, str]:
    env = UnityPy.load(data)
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            asset = obj.read()
            return asset.name, bytes(asset.script).decode()


def parse_script(script: str) -> list[dict[str, str | None]]:
    messages = []
    # Utage는 콤마(,)나 탭으로 구분된 형식을 사용함
    for line in script.split('\n'):
        parts = line.split(',')
        if len(parts) < 3: continue
        
        # Utage의 대사 명령어(보통 'Page' 또는 빈칸)를 찾음
        # 게임마다 구조가 다르므로 'Text'나 'Message'가 포함된 열을 찾아야 함
        if "Text" in parts or any(p.strip() for p in parts[2:4]): 
            # 몬무스 TD의 실제 대사 위치에 맞게 인덱스(1, 2, 3...) 조정 필요
            name = parts[1].strip()
            message = parts[2].strip()
            
            if message and not message.startswith("["): # 태그 제외
                messages.append({
                    'name': name,
                    'message': message.replace('<br>', r'\n')
                })
    return messages