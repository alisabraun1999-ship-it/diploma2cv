# app/routes.py
from flask import render_template, request, jsonify, send_from_directory, redirect, Response, flash, session, get_flashed_messages
from app import app
import os
import json
from pathlib import Path
from app.plan_parser import parse_all_curriculums, parse_single_curriculum
from werkzeug.utils import secure_filename
from app.diploma_parser import process_diploma

# Конфигурация загрузки файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Конфигурация для дипломов
DIPLOMA_UPLOAD_FOLDER = 'data/diplomas'
app.config['DIPLOMA_UPLOAD_FOLDER'] = DIPLOMA_UPLOAD_FOLDER

# Секретный ключ для сессий
app.config['SECRET_KEY'] = 'diploma2cv-secret-key-2024'

# Создаем директории если их нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data/parsed', exist_ok=True)
os.makedirs(DIPLOMA_UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def json_response(data, status=200):
    """Вспомогательная функция для возврата JSON с кириллицей"""
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8',
        status=status
    )

@app.route('/')
def index():
    """Главная страница с отображением результатов загрузки"""
    upload_result = session.pop('upload_result', None) if 'upload_result' in session else None
    flashes = get_flashed_messages(with_categories=True)
    flash_messages = []
    
    for category, message in flashes:
        flash_messages.append({'category': category, 'message': message})
        
    return render_template('index.html',
                         upload_result=upload_result,
                         flash_messages=flash_messages)

@app.route('/api/file_count')
def file_count():
    """Возвращает количество файлов учебных планов"""
    try:
        data_dir = 'data'
        if not os.path.exists(data_dir):
            return json_response({'count': 0, 'message': 'Папка data не найдена'})
            
        excel_files = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                excel_files.append(filename)
                
        return json_response({
            'count': len(excel_files),
            'files': excel_files,
            'status': 'success'
        })
    except Exception as e:
        return json_response({'error': str(e)}, 500)

@app.route('/process_all_plans')
def process_all_plans():
    """Обработать все учебные планы и показать результаты"""
    try:
        results = parse_all_curriculums()
        flash('✅ Все учебные планы успешно обработаны!', 'success')
        return redirect('/results')
    except Exception as e:
        flash(f'❌ Ошибка обработки: {str(e)}', 'error')
        return redirect('/')

@app.route('/upload_plan', methods=['POST'])
def upload_plan():
    """Загрузить и обработать один учебный план"""
    try:
        if 'file' not in request.files:
            flash('❌ Нет файла в запросе', 'error')
            return redirect('/')
            
        file = request.files['file']
        if file.filename == '':
            flash('❌ Файл не выбран', 'error')
            return redirect('/')
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            result = parse_single_curriculum(file_path)
            
            if 'error' in result:
                flash(f'❌ Ошибка обработки: {result["error"]}', 'error')
                return redirect('/')
                
            session['upload_result'] = {
                'type': 'plan',
                'filename': filename,
                'disciplines_count': len(result.get('disciplines', [])),
                'data': result
            }
            
            flash(f'✅ Файл "{filename}" успешно обработан! Найдено {len(result.get("disciplines", []))} дисциплин', 'success')
            return redirect('/')
            
        flash('❌ Недопустимый тип файла. Разрешены только XLSX/XLS', 'error')
        return redirect('/')
        
    except Exception as e:
        flash(f'❌ Ошибка при загрузке файла: {str(e)}', 'error')
        return redirect('/')

@app.route('/upload_diploma', methods=['POST'])
def upload_diploma():
    """Загружает и обрабатывает PDF диплом"""
    try:
        if 'file' not in request.files:
            flash('❌ Нет файла в запросе', 'error')
            return redirect('/')
            
        file = request.files['file']
        if file.filename == '':
            flash('❌ Файл не выбран', 'error')
            return redirect('/')
            
        student_name = request.form.get('student_name', '').strip()
        if not student_name:
            flash('❌ Укажите ФИО студента', 'error')
            return redirect('/')

        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['DIPLOMA_UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            result = process_diploma(file_path, student_name=student_name)
            
            if 'error' in result:
                flash(f'❌ Ошибка обработки диплома: {result["error"]}', 'error')
                return redirect('/')
                
            # Гарантируем структуру
            if 'data' not in result:
                result['data'] = result
            
            session['upload_result'] = {
                'type': 'diploma',
                'filename': filename,
                'disciplines_count': len(result['data']['disciplines']),
                'data': result['data']
            }
            
            flash(f'✅ Диплом "{filename}" успешно обработан! Студент: {student_name}. Найдено {len(result["data"]["disciplines"])} дисциплин', 'success')
            return redirect('/')
            
        flash('❌ Только PDF файлы разрешены', 'error')
        return redirect('/')
        
    except Exception as e:
        flash(f'❌ Ошибка при загрузке диплома: {str(e)}', 'error')
        return redirect('/')

@app.route('/results')
def show_results():
    """Показывает результаты парсинга всех учебных планов"""
    try:
        summary_file = Path("data/parsed/parsing_summary.json")
        if not summary_file.exists():
            return render_template('results.html',
                                 error="Результаты не найдены. Запустите обработку сначала.")
                                 
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
            
        results = []
        total_disciplines = 0
        total_competences = 0
        processed_files = 0
        
        for filename, file_info in summary_data.items():
            if file_info['status'] == 'success':
                json_filename = filename.replace('.xlsx', '_parsed.json').replace('.xls', '_parsed.json')
                json_path = Path("data/parsed") / json_filename
                
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        
                    results.append({
                        'filename': filename,
                        'disciplines_count': file_info['disciplines_count'],
                        'competences_count': file_info['competences_count'],
                        'disciplines': file_data.get('disciplines', [])[:15],
                        'output_file': file_info['output_file']
                    })
                    
                    total_disciplines += file_info['disciplines_count']
                    total_competences += file_info['competences_count']
                    processed_files += 1
                    
        return render_template('results.html',
                             results=results,
                             total_disciplines=total_disciplines,
                             total_competences=total_competences,
                             total_files=processed_files,
                             summary_data=summary_data)
                             
    except Exception as e:
        return render_template('results.html', error=f"Ошибка: {str(e)}")

@app.route('/data/parsed/<path:filename>')
def serve_parsed_file(filename):
    """Отдает файлы из папки data/parsed для веб-интерфейса"""
    try:
        return send_from_directory('data/parsed', filename)
    except FileNotFoundError:
        return json_response({'error': 'Файл не найден'}, 404)

@app.route('/api/parsed_results')
def api_parsed_results():
    """API для получения результатов парсинга"""
    try:
        summary_file = Path("data/parsed/parsing_summary.json")
        if not summary_file.exists():
            return json_response({'error': 'Результаты не найдены'}, 404)
            
        with open(summary_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return json_response({'success': True, 'data': data})
    except Exception as e:
        return json_response({'error': str(e)}, 500)

@app.route('/test_diploma')
def test_diploma():
    """Тестовый маршрут для проверки парсера"""
    try:
        test_file = "data/diplomas/ГМУ.pdf"
        if os.path.exists(test_file):
            result = process_diploma(test_file, student_name="Титов Дмитрий Михайлович")
            return jsonify(result)
        else:
            return jsonify({"error": "Тестовый файл не найден"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/test')
def test():
    return "Тестовый маршрут работает! ✅"

# Убраны error.html
@app.errorhandler(404)
def not_found_error(error):
    return "<h1>404 — Страница не найдена</h1>", 404

@app.errorhandler(500)
def internal_error(error):
    return "<h1>500 — Ошибка сервера</h1>", 500