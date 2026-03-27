import re
from pathlib import Path
from utils import read_json, write_json

class Merger:
    def __init__(self, translation_dir: str | Path, cache_dir: str | Path):
        self.translation_dir = Path(translation_dir)
        self.cache_dir = Path(cache_dir)

    def run(self):
        self.merge_novels()
        self.merge_words()

    def merge_novels(self):
        for file in self.cache_dir.glob('*.json'):
            match = re.search(r'\d+', file.stem)
            if not match: continue
            novel_id = match.group()
            cache = read_json(file)
            translation = {
                msg['pre_jp'].replace(r'\n', '<br>'): msg['post_zh_preview'].replace(r'\n', '<br>')
                for msg in cache
            }
            # montrans/novels/ID/ko_KR.json 형태로 저장 (한국어 기준)
            write_json(self.translation_dir / f'novels/{novel_id}/ko_KR.json', translation)

    def merge_words(self):
        # 단어 병합 로직 (MonTransl 경로 사용)
        cache_path = self.cache_dir / 'words.json'
        if not cache_path.exists(): return
        words_path = self.translation_dir / 'words/ko_KR.json'
        words = read_json(words_path) if words_path.exists() else {}
        cache = read_json(cache_path)
        words.update({msg['pre_jp']: msg['post_zh_preview'] for msg in cache})
        write_json(words_path, words)

if __name__ == '__main__':
    Merger(
        translation_dir='.', # montrans 루트
        cache_dir='MonTransl/sampleProject/transl_cache' #
    ).run()