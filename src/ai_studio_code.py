import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- НАСТРОЙКИ ---
# Укажите путь к вашему файлу с ключами сервисного аккаунта
CREDENTIALS_PATH = '../config/service_account.json' 
# --- КОНЕЦ НАСТРОЕК ---

def audit_service_account_storage(credentials_file):
    """
    Подключается от имени сервисного аккаунта и выводит список всех файлов,
    владельцем которых он является, а также подсчитывает их общий размер.
    """
    if not os.path.exists(credentials_file):
        print(f"❌ Файл с учетными данными не найден: {credentials_file}")
        return

    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Успешная аутентификация от имени сервисного аккаунта.")
    except Exception as e:
        print(f"❌ Ошибка аутентификации: {e}")
        return

    files_found = []
    total_size_bytes = 0
    page_token = None

    print("\n🔍 Поиск файлов, принадлежащих сервисному аккаунту...")

    try:
        while True:
            # Ищем все файлы, где владелец - 'me' (т.е. этот сервисный аккаунт)
            response = drive_service.files().list(
                q="'me' in owners",
                spaces='drive',
                fields='nextPageToken, files(id, name, size, createdTime)',
                pageToken=page_token
            ).execute()

            files = response.get('files', [])
            files_found.extend(files)
            
            for file in files:
                # Поле 'size' может отсутствовать у Google Docs/Sheets, но для них размер = 0
                file_size = int(file.get('size', 0))
                total_size_bytes += file_size

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

    except HttpError as error:
        print(f"❌ Произошла ошибка API: {error}")
        return

    print("-" * 60)
    if not files_found:
        print("🎉 Хранилище сервисного аккаунта абсолютно пустое.")
    else:
        print(f"📊 Найдено файлов: {len(files_found)}")
        for f in files_found:
            size_mb = int(f.get('size', 0)) / (1024 * 1024)
            print(f"  - Имя: {f['name']} (ID: {f['id']})")
            print(f"    Создан: {f['createdTime']}, Размер: {size_mb:.4f} MB")
        
        total_size_gb = total_size_bytes / (1024 * 1024 * 1024)
        print("-" * 60)
        print(f"📈 ОБЩИЙ РАЗМЕР ВСЕХ ФАЙЛОВ: {total_size_gb:.4f} GB")
        print(f"   (Лимит хранилища сервисного аккаунта: 15.0 GB)")

        # --- Код для удаления файлов (используйте с осторожностью!) ---
        # print("\n🗑️ Чтобы удалить все найденные файлы, раскомментируйте код ниже.")
        # confirm = input("Вы уверены, что хотите удалить ВСЕ эти файлы? (yes/no): ")
        # if confirm.lower() == 'yes':
        #     print("Удаление файлов...")
        #     for f in files_found:
        #         try:
        #             drive_service.files().delete(fileId=f['id']).execute()
        #             print(f"  - Файл '{f['name']}' удален.")
        #         except HttpError as error:
        #             print(f"  - Не удалось удалить файл '{f['name']}': {error}")
        #     print("✅ Очистка завершена.")

if __name__ == '__main__':
    audit_service_account_storage(CREDENTIALS_PATH)