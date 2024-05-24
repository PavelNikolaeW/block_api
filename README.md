# block_api

1. ставим postgres
2. создаем таблицу и юзера
3. скачиваем репозиторий
4. создаем .env файл 
   1. прописываем туда
        POSTGRES_USER=
        POSTGRES_PASSWD=
        POSTGRES_NAME=
5. ./manage.py makemigrations
6. ./manage.py migrate
7. ./manage.py createsuperuser
8. через админку создаем пару блоков
9. ставим фронт 