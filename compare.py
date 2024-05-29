import json
import os
import requests
from deepdiff import DeepDiff
from swagger_spec_validator.validator20 import validate_spec
from swagger_spec_validator.common import SwaggerValidationError
from datetime import datetime


def load_spec(file_path_or_url):
    """Загружает спецификацию из JSON файла или URL."""
    try:
        if file_path_or_url.startswith('http://') or file_path_or_url.startswith('https://'):
            response = requests.get(file_path_or_url)
            response.raise_for_status()
            spec = response.json()
        else:
            with open(file_path_or_url, 'r') as file:
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


def save_spec(spec, file_path):
    """Сохраняет спецификацию в JSON файл с временной меткой."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path_with_timestamp = file_path.replace('.json', f'_{timestamp}.json')
    with open(file_path_with_timestamp, 'w') as file:
        json.dump(spec, file, indent=4)


def get_latest_spec_in_range(directory, base_filename, start_time=None, end_time=None):
    """Получает последнюю спецификацию в указанном диапазоне времени или самую свежую."""
    latest_spec = None
    latest_time = None

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


def main(current_spec_path, directory, base_filename, start_time=None, end_time=None):
    """Основная функция для загрузки, сравнения и сохранения спецификаций."""
    # Загрузить текущую спецификацию
    current_spec = load_spec(current_spec_path)
    if not current_spec:
        print("Текущая спецификация невалидна. Завершение работы.")
        return

    # Определить последнюю предыдущую спецификацию в указанном диапазоне времени
    latest_spec_path = get_latest_spec_in_range(directory, base_filename, start_time, end_time)
    previous_spec = load_spec(latest_spec_path) if latest_spec_path else None

    # Сравнить спецификации
    if previous_spec:
        changes = compare_specs(current_spec, previous_spec)
        if changes:
            print("Найдены изменения в спецификации:")
            print(
                json.dumps(changes, indent=4, default=str))  # Преобразование изменений в строку для сериализации в JSON
        else:
            print("Изменений в спецификации не найдено.")
    else:
        print("Предыдущая спецификация не найдена или невалидна. Создается новый файл.")

    # Сохранить текущую спецификацию как предыдущую для следующего сравнения
    save_spec(current_spec, os.path.join(directory, base_filename + '.json'))


if __name__ == "__main__":
    current_spec_path = 'https://petstore.swagger.io/v2/swagger.json'  # URL или путь к текущей спецификации
    directory = './specs'  # Директория для хранения спецификаций
    base_filename = 'previous_spec'  # Базовое имя для хранения предыдущих спецификаций

    # Пример для использования абсолютного диапазона времени
    start_time_str = '2024-05-01 00:00:00'  # Задайте начальную дату и время
    end_time_str = '2024-05-30 00:00:00'  # Задайте конечную дату и время

    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S') if start_time_str else None
    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S') if end_time_str else None

    main(current_spec_path, directory, base_filename, start_time, end_time)
