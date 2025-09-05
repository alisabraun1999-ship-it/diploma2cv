# test_simple.py
import subprocess
import os

print("🔍 Проверяем систему...")

# Проверяем poppler
try:
    result = subprocess.run(['pdftoppm', '-v'], capture_output=True, text=True)
    print("✅ Poppler работает")
except:
    print("❌ Poppler не работает")

# Проверяем tesseract
try:
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    print("✅ Tesseract работает")
except:
    print("❌ Tesseract не работает")

# Проверяем папки
folders = ['data', 'data/diplomas']
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"📁 Создана папка: {folder}")
    else:
        print(f"✅ Папка существует: {folder}")

# Проверяем файлы
pdf_files = [f for f in os.listdir('data/diplomas') if f.endswith('.pdf')]
if pdf_files:
    print(f"✅ Найдены PDF файлы: {pdf_files}")
else:
    print("❌ В папке data/diplomas нет PDF файлов")
    print("Добавьте PDF файл в папку data/diplomas/")