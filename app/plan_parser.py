# app/plan_parser.py
import pandas as pd
import json
import os
import re
from typing import Dict, List, Any
from pathlib import Path

def parse_single_curriculum(file_path: str) -> Dict[str, Any]:
    """
    Исправленный парсер для вашей структуры файлов
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔍 Парсим файл: {os.path.basename(file_path)}")
        
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        # Парсим компетенции из Компетенции(2)
        competences_dict = {}
        if 'Компетенции(2)' in sheet_names:
            try:
                comp_df = pd.read_excel(file_path, sheet_name='Компетенции(2)', header=None)
                print(f"📏 Размер листа компетенций: {comp_df.shape}")
                
                for index, row in comp_df.iterrows():
                    if row.isna().all():
                        continue
                    
                    # Ищем строки с дисциплинами (начинаются с Б1.О.XX)
                    disc_code = ""
                    disc_competences = []
                    
                    for i, cell in enumerate(row):
                        if pd.notna(cell):
                            cell_str = str(cell).strip()
                            
                            # Код дисциплины (например: Б1.О.01)
                            if cell_str.startswith('Б1.О.') and len(cell_str) >= 7:
                                disc_code = cell_str
                            
                            # Компетенции (содержат УК- или ОПК- или ПК-)
                            elif 'УК-' in cell_str or 'ОПК-' in cell_str or 'ПК-' in cell_str:
                                # Извлекаем все компетенции из строки
                                comp_matches = re.findall(r'(УК-\d+|ОПК-\d+|ПК-\d+)', cell_str)
                                disc_competences.extend(comp_matches)
                    
                    if disc_code and disc_competences:
                        competences_dict[disc_code] = disc_competences
                        print(f"✅ {disc_code} → {disc_competences}")
                
            except Exception as e:
                print(f"❌ Ошибка парсинга компетенций: {e}")
        
        # Парсим дисциплины из листа План
        disciplines_list = []
        if 'План' in sheet_names:
            try:
                plan_df = pd.read_excel(file_path, sheet_name='План', header=None)
                print(f"📏 Размер листа плана: {plan_df.shape}")
                
                # Находим заголовки - строка 2 содержит названия столбцов
                header_row = 2
                header_cells = plan_df.iloc[header_row]
                
                # Определяем индексы столбцов
                code_col = None
                name_col = None
                credits_col = None
                
                for j, cell in enumerate(header_cells):
                    if pd.notna(cell):
                        cell_str = str(cell).lower()
                        if any(keyword in cell_str for keyword in ['индекс', 'код']):
                            code_col = j
                        elif any(keyword in cell_str for keyword in ['наименован', 'назван']):
                            name_col = j
                        elif any(keyword in cell_str for keyword in ['з.е.', 'кредит', 'зачет']):
                            credits_col = j
                
                print(f"🎯 Столбцы: код={code_col}, название={name_col}, кредиты={credits_col}")
                
                # Парсим дисциплины начиная со строки 3
                for i in range(3, len(plan_df)):
                    row = plan_df.iloc[i]
                    
                    if row.isna().all():
                        continue
                    
                    # Извлекаем данные
                    disc_code = str(row[code_col]).strip() if code_col is not None and pd.notna(row[code_col]) else ""
                    disc_name = str(row[name_col]).strip() if name_col is not None and pd.notna(row[name_col]) else ""
                    
                    # Пропускаем служебные строки
                    if (not disc_code or not disc_name or
                        any(keyword in disc_code.lower() for keyword in ['блок', 'итого', 'всего', 'раздел', 'часть']) or
                        any(keyword in disc_name.lower() for keyword in ['блок', 'итого', 'всего', 'раздел', 'часть'])):
                        continue
                    
                    # Пропускаем если это не код дисциплины
                    if not disc_code.startswith('Б1.О.'):
                        continue
                    
                    # Извлекаем кредиты
                    credits = 0.0
                    if credits_col is not None and pd.notna(row[credits_col]):
                        try:
                            credits = float(row[credits_col])
                        except:
                            pass
                    
                    # Находим компетенции для этой дисциплины
                    disc_competences = competences_dict.get(disc_code, [])
                    
                    discipline_data = {
                        "code": disc_code,
                        "name": disc_name,
                        "credits": credits,
                        "hours_total": 0,  # Пока не нашли часы
                        "competences": disc_competences
                    }
                    
                    disciplines_list.append(discipline_data)
                    print(f"✅ Дисциплина: {disc_code} - {disc_name} ({credits} з.е.)")
                
            except Exception as e:
                print(f"❌ Ошибка парсинга дисциплин: {e}")
        
        # Если не нашли в основном плане, пробуем ПланСвод
        if not disciplines_list and 'ПланСвод' in sheet_names:
            try:
                plan_df = pd.read_excel(file_path, sheet_name='ПланСвод', header=None)
                print("🔄 Пробуем парсить ПланСвод...")
                
                # Аналогичный парсинг для ПланСвод
                for i in range(3, len(plan_df)):
                    row = plan_df.iloc[i]
                    
                    if row.isna().all():
                        continue
                    
                    disc_code = str(row[1]).strip() if pd.notna(row[1]) else ""
                    disc_name = str(row[2]).strip() if pd.notna(row[2]) else ""
                    
                    if (disc_code.startswith('Б1.О.') and disc_name and
                        not any(keyword in disc_code.lower() for keyword in ['блок', 'итого', 'всего'])):
                        
                        # Пытаемся найти кредиты
                        credits = 0.0
                        if pd.notna(row[7]):  # Столбец с кредитами
                            try:
                                credits = float(row[7])
                            except:
                                pass
                        
                        disc_competences = competences_dict.get(disc_code, [])
                        
                        discipline_data = {
                            "code": disc_code,
                            "name": disc_name,
                            "credits": credits,
                            "hours_total": 0,
                            "competences": disc_competences
                        }
                        
                        disciplines_list.append(discipline_data)
                        print(f"✅ Дисциплина (свод): {disc_code} - {disc_name}")
                
            except Exception as e:
                print(f"❌ Ошибка парсинга ПланСвод: {e}")
        
        print(f"📊 Итог: {len(disciplines_list)} дисциплин, {len(competences_dict)} соответствий")
        
        return {
            "source_file": os.path.basename(file_path),
            "disciplines": disciplines_list,
            "competences_mapping": competences_dict
        }
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return {"error": str(e), "source_file": os.path.basename(file_path)}

def parse_all_curriculums(data_dir: str = "data", output_dir: str = "data/parsed") -> Dict[str, Any]:
    """Парсит все файлы учебных планов"""
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    data_path = Path(data_dir)
    excel_files = list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xls"))
    
    print(f"📁 Найдено {len(excel_files)} файлов для обработки")
    
    for file_path in excel_files:
        print(f"\n{'='*60}")
        result = parse_single_curriculum(str(file_path))
        
        if "error" not in result:
            output_file = os.path.join(output_dir, f"{file_path.stem}_parsed.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
            
            results[file_path.name] = {
                "status": "success",
                "disciplines_count": len(result.get("disciplines", [])),
                "competences_count": len(result.get("competences_mapping", {})),
                "output_file": output_file
            }
            
            print(f"✅ Успешно: {len(result.get('disciplines', []))} дисциплин")
        else:
            results[file_path.name] = {
                "status": "error",
                "error": result["error"]
            }
            print(f"❌ Ошибка: {result['error']}")
    
    # Сводный отчет
    summary_file = os.path.join(output_dir, "parsing_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\n🎉 Обработка завершена!")
    return results

# Для тестирования
if __name__ == "__main__":
    # Тестируем первый файл
    data_path = Path("data")
    excel_files = list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xls"))
    
    if excel_files:
        test_file = str(excel_files[0])
        print("🧪 Тестируем парсер на первом файле")
        result = parse_single_curriculum(test_file)
        
        if result.get('disciplines'):
            print(f"\n📋 Найдены дисциплины:")
            for disc in result['disciplines'][:10]:  # Первые 10
                comps = ", ".join(disc['competences']) if disc['competences'] else "нет"
                print(f"   {disc['code']}: {disc['name']} ({disc['credits']} з.е.) → {comps}")
        else:
            print("❌ Дисциплины не найдены")
    else:
        print("❌ Файлы не найдены")