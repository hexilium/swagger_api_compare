import json
import os
import requests
from deepdiff import DeepDiff
from swagger_spec_validator.validator20 import validate_spec
from swagger_spec_validator.common import SwaggerValidationError
from datetime import datetime
from urllib.parse import urlparse

cur_spec = 'current'
diff = 'differences'

def load_spec(file_path_or_url):
    """Загружает спецификацию из JSON файла или URL."""
    try:
        if file_path_or_url.startswith('http://') or file_path_or_url.startswith('https://'):
            response = requests.get(file_path_or_url)
            response.raise_for_status()
            response.encoding = 'utf-8'  # Устанавливаем кодировку
            try:
                spec = response.json()
            except json.JSONDecodeError:
                print(f"Ответ по URL {file_path_or_url} не содержит допустимый JSON.")
                return None
        else:
            with open(file_path_or_url, 'r', encoding='utf-8') as file:
                spec = json.load(file)
        # Проверка на валидность спецификации Swagger
        validate_spec(spec)
        return spec
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке спецификации по URL: {e}")
        return None
    except FileNotFoundError:
        print(f"Файл {file_path_or_url} не найден.")
        return None
    except json.JSONDecodeError:
        print(f"Файл {file_path_or_url} содержит недопустимый JSON.")
        return None
    except SwaggerValidationError as e:
        print(f"Файл {file_path_or_url} содержит недопустимую спецификацию Swagger: {e}")
        return None


def save_spec(spec, directory, base_filename):
    """Сохраняет спецификацию в JSON файл с временной меткой."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path_with_timestamp = os.path.join(directory, f"{base_filename}_{timestamp}.json")
    with open(file_path_with_timestamp, 'w', encoding='utf-8') as file:
        json.dump(spec, file, indent=4)


def save_diff(diff, directory, base_filename):
    """Сохраняет результат сравнения в JSON файл с временной меткой."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path_with_timestamp = os.path.join(directory, f"{base_filename}_diff_{timestamp}.json")
    with open(file_path_with_timestamp, 'w', encoding='utf-8') as file:
        json.dump(diff, file, indent=4, default=str)


def get_latest_spec_in_range(directory, base_filename, start_time=None, end_time=None):
    """Получает последнюю спецификацию в указанном диапазоне времени или самую свежую."""
    latest_spec = None
    latest_time = None

    if not os.path.exists(directory):
        return None

    for filename in os.listdir(directory):
        if filename.startswith(base_filename) and filename.endswith('.json'):
            timestamp_str = filename[len(base_filename) + 1:-5]
            try:
                file_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                if (start_time is None or file_time >= start_time) and (end_time is None or file_time <= end_time):
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
                        latest_spec = os.path.join(directory, filename)
            except ValueError:
                continue

    return latest_spec


def compare_specs(current_spec, previous_spec):
    """Сравнивает текущую и предыдущую спецификации."""
    diff = DeepDiff(previous_spec, current_spec, ignore_order=True)
    return diff


def extract_default_directory(url):
    """Извлекает третий уровень с конца в пути URL."""
    path_parts = urlparse(url).path.split('/')
    if len(path_parts) >= 2:
        return path_parts[-2]
    return '.'


def process_url(current_spec_url, base_filename, work_dir, start_time=None, end_time=None):
    """Процесс сравнения для одного URL."""
    default_directory = extract_default_directory(current_spec_url)

    current_spec_directory = os.path.join(work_dir, cur_spec, default_directory)
    diff_directory = os.path.join(work_dir, diff, default_directory)

    # Устанавливаем префикс файла по умолчанию, если он не указан
    if base_filename is None:
        base_filename = default_directory

    current_spec = load_spec(current_spec_url)
    if not current_spec:
        print(f"Текущая спецификация по URL {current_spec_url} невалидна. Пропуск.")
        return

    latest_spec_path = get_latest_spec_in_range(current_spec_directory, base_filename, start_time, end_time)
    previous_spec = load_spec(latest_spec_path) if latest_spec_path else None

    if previous_spec:
        changes = compare_specs(current_spec, previous_spec)
        if changes:
            print(f"Найдены изменения в спецификации по URL {current_spec_url}:")
            save_diff(changes, diff_directory, base_filename)
        else:
            print(f"Изменений в спецификации по URL {current_spec_url} не найдено.")
    else:
        print(f"Предыдущая спецификация по URL {current_spec_url} не найдена или невалидна. Создается новый файл.")

    save_spec(current_spec, current_spec_directory, base_filename)


def main(urls_file, work_dir='.', base_filename=None, start_time=None, end_time=None):
    """Основная функция для загрузки, сравнения и сохранения спецификаций для нескольких URL."""
    with open(urls_file, 'r', encoding='utf-8') as file:
        urls = [line.strip() for line in file if line.strip()]

    for url in urls:
        process_url(url, base_filename, work_dir, start_time, end_time)


if __name__ == "__main__":
    urls_file = 'urls.txt'  # Файл с URL-адресами

    # Пример для использования абсолютного диапазона времени
    start_time_str = '2023-05-01 00:00:00'  # Задайте начальную дату и время
    end_time_str = '2023-06-01 00:00:00'  # Задайте конечную дату и время

    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S') if start_time_str else None
    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S') if end_time_str else None

    # Указываем рабочую директорию (например, "C:\\results")
    work_dir = "C:\\results"

    main(urls_file, work_dir)
