# block_api

1. ставим postgres
   1. создаем таблицу и юзера
   2. запускаем
3. скачиваем этот репозиторий
   1. устанавливаем зависимости django и django rest framework (мб еще каие то)
5. в корне проекта создаем .env файл 
   1. прописываем туда
        POSTGRES_USER=
        POSTGRES_PASSWD=
        POSTGRES_NAME=
6. ./manage.py makemigrations
7. ./manage.py migrate
8. ./manage.py createsuperuser
   1. создаем супер юзера
9. ./manage.py runserver
10. через админку создаем пару блоков (это тоже нужно сделать)
11. ставим фронт 
