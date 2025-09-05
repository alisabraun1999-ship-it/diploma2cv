# run.py
from app import app

if __name__ == '__main__':
    print("Запуск Flask приложения...")
    app.run(debug=True, host='0.0.0.0', port=5000)