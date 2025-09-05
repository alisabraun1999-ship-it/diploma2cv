# app/diploma_parser.py
import PyPDF2
import pdfplumber
import re
import os
import json
import tempfile
import subprocess
from typing import Dict, List, Any
from pathlib import Path

class OCRProcessor:
    @staticmethod
    def is_tesseract_available():
        try:
            result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def extract_text_with_ocr(file_path: str) -> str:
        text = ""
        try:
            print("🔄 Запускаем OCR обработку...")
            if not os.path.exists(file_path):
                print(f"❌ Файл не существует: {file_path}")
                return ""

            from pdf2image import convert_from_path
            from PIL import Image, ImageEnhance

            print("📊 Конвертируем PDF в изображения...")
            try:
                images = convert_from_path(file_path, dpi=400, thread_count=2)
                print(f"✅ Получено {len(images)} страниц")
            except Exception as e:
                print(f"❌ Ошибка конвертации PDF: {e}")
                return ""

            for i, image in enumerate(images):
                try:
                    print(f"🔍 Обрабатываем страницу {i+1}/{len(images)}...")
                    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    image_path = temp_file.name
                    temp_file.close()

                    img = image.convert('L')
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(2.5)
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(2.0)
                    img.save(image_path, 'PNG', quality=100)

                    print("   Распознаем текст...")
                    result = subprocess.run([
                        'tesseract', image_path, 'stdout', '-l', 'rus+eng', '--psm', '6'
                    ], capture_output=True, timeout=120)

                    if result.returncode == 0:
                        page_text = result.stdout.decode('utf-8', errors='ignore').strip()
                        if page_text:
                            text += f"--- Страница {i+1} ---\n{page_text}\n\n"
                            print(f"   ✅ Распознано {len(page_text)} символов")
                        else:
                            print(f"   ⚠️ Текст не распознан")
                    else:
                        print(f"   ❌ Ошибка Tesseract")

                    try:
                        os.unlink(image_path)
                    except:
                        pass

                except Exception as e:
                    print(f"❌ Ошибка страницы {i+1}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Ошибка OCR: {e}")
        return text


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    print(f"🔍 Обрабатываю файл: {os.path.basename(file_path)}")
    try:
        print("🔄 Пробую OCR...")
        ocr_text = OCRProcessor.extract_text_with_ocr(file_path)
        if ocr_text.strip():
            text = ocr_text
            print(f"👁️ OCR: {len(text)} символов")
        else:
            print("❌ OCR не дал результатов")
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    text += "\n\n"
    except Exception as e:
        print(f"❌ Ошибка извлечения текста: {e}")
    print(f"✅ Итого извлечено: {len(text)} символов")
    return text


def parse_diploma_text(text: str) -> Dict[str, Any]:
    """Парсит диплом: специальность, год, дисциплины"""
    result = {
        "specialty": "Не найдено",
        "graduation_year": "Не найден",
        "disciplines": []
    }

    # === ПОИСК СПЕЦИАЛЬНОСТИ ===
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    full_text = " ".join(lines).lower()

    if '38.03.04' in full_text or 'государственное и муниципальное управление' in full_text:
        result["specialty"] = "38.03.04 Государственное и муниципальное управление"
    elif '09.03.03' in full_text or 'прикладная информатика' in full_text:
        result["specialty"] = "09.03.03 Прикладная информатика"

    # === ПОИСК ГОДА ===
    for line in lines:
        if 'аттестат о среднем общем образовании' in line.lower() or 'cpeHeM oomeM oopa3OBaHin' in line:
            year_match = re.search(r'(202[0-9])', line)
            if year_match:
                result["graduation_year"] = year_match.group(1)
                break

    # === ПОИСК ДИСЦИПЛИН ===
    in_section = False
    for line in lines:
        if not in_section and any(kw in line.lower() for kw in ['наименование', 'амсициплины', 'amci', 'дисципли']):
            in_section = True
            continue
        if not in_section:
            continue
        if any(kw in line.lower() for kw in ['дополнительные', 'подпись', 'итого', 'приложение']):
            break

        # Чистим строку
        clean = re.sub(r'\s*\d+\.?\d*\s*[ез\.]+\s*', ' ', line)
        clean = re.sub(r'[^\w\sа-яёА-ЯЁ\-]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Поиск оценки с нормализацией
        grade = "неизвестно"
        word = clean.upper()

        if any(x in word for x in ['ОТЛИЧНО', '5', 'OTJIM4HO', 'OTIH4HO', 'OTNBO', 'OTI4HO', 'OTJILYHO', 'OTJIEIHHO']):
            grade = "5"
        elif any(x in word for x in ['ХОРОШО', '4', 'XOPOMO', 'XOPOO', 'ONCHO', 'ONLHO']):
            grade = "4"
        elif any(x in word for x in ['УДОВЛЕТВОРИТЕЛЬНО', '3', 'YAO', '3a4TeHo', '3a4TCH0', '3aTeHo']):
            grade = "3"
        elif any(x in word for x in ['ЗАЧТЕНО', 'ЗАЧЕТ', '3A4TEH', '3a4TeHo', '3ayTeHo']):
            grade = "зачтено"
        elif any(x in word for x in ['НЕУД', '2']):
            grade = "2"

        if grade != "неизвестно":
            # Удаляем оценку и артефакты
            name = re.sub(r'\s+(отлично|хорошо|удовлетворительно|зачтено|зачет|неуд|5|4|3|2|OTJIM4HO|OTIH4HO|3a4TeHo|3a4TCH0|3aTeHo|3a4TCHO|ONCHO|ONLHO).*$', '', clean, flags=re.IGNORECASE)
            name = re.sub(r'\s+', ' ', name).strip()
            if name and len(name) > 3:
                result["disciplines"].append({
                    "name": name,
                    "grade": grade
                })

    return result  # ✅ Правильно: return внутри функции


def process_diploma(file_path: str, student_name: str = None) -> Dict[str, Any]:
    """Обрабатывает диплом"""
    print(f"\n🎯 Обрабатываю диплом: {os.path.basename(file_path)}")
    print("=" * 50)

    if not os.path.exists(file_path):
        return {"error": "Файл не существует"}

    file_size = os.path.getsize(file_path)
    print(f"📏 Размер файла: {file_size} байт")
    if file_size == 0:
        return {"error": "Файл пустой"}

    text = extract_text_from_pdf(file_path)
    if not text.strip():
        return {"error": "Не удалось извлечь текст"}

    parsed = parse_diploma_text(text)
    disciplines_count = len(parsed["disciplines"])

    # Гарантируем правильную структуру
    result = {
        "source_file": os.path.basename(file_path),
        "type": "diploma",
        "data": {
            "student_name": student_name or "Не указано",
            "specialty": parsed["specialty"],
            "graduation_year": parsed["graduation_year"],
            "disciplines": parsed["disciplines"]
        },
        "disciplines_count": disciplines_count
    }

    # Сохраняем
    output_dir = "data/parsed_diplomas"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{Path(file_path).stem}_parsed.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print("=" * 50)
    print(f"✅ Обработка завершена!")
    print(f"📊 Результаты:")
    print(f"   👤 Студент: {result['data']['student_name']}")
    print(f"   🎓 Специальность: {result['data']['specialty']}")
    print(f"   📅 Год: {result['data']['graduation_year']}")
    print(f"   📚 Дисциплин: {disciplines_count}")

    return result