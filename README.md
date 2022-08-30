Список необходимых пакетов в файле requirements.txt<br>
Так же необходимо установить redis и celery.<br>
Для запуска сервера редис необходимо в терминале ввести команду "redis-server".<br>
Для запуска celery beat необходимо в терминале ввести "celery -A zs_integration_module  beat".<br>
Для запуска celery необходимо ввести команду "celery -A zs_integration_module  worker --loglevel INFO".<br>
