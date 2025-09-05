# check_results.py
import json
import os
from pathlib import Path

def check_parsing_results():
    print("🔍 Проверяем результаты парсинга...")
    
    parsed_dir = Path("data/parsed")
    if not parsed_dir.exists():
        print("❌ Папка data/parsed не существует!")
        return False
    
    json_files = list(parsed_dir.glob("*.json"))
    print(f"📁 Найдено JSON файлов: {len(json_files)}")
    
    for json_file in json_files:
        print(f"   - {json_file.name}")
    
    # Проверяем summary файл
    summary_file = parsed_dir / "parsing_summary.json"
    if summary_file.exists():
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            print(f"✅ Summary файл: {len(summary_data)} записей")
            return True
        except Exception as e:
            print(f"❌ Ошибка чтения summary: {e}")
            return False
    else:
        print("❌ Файл parsing_summary.json не найден")
        return False

if __name__ == "__main__":
    check_parsing_results()