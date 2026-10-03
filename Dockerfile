FROM python:3.12-slim
WORKDIR /app
COPY ma_liste.py .
# Mode en ligne + données sur le disque persistant monté sur /data
ENV MA_LISTE_ONLINE=1 \
    MA_LISTE_DATA=/data \
    PYTHONUNBUFFERED=1
# MA_LISTE_USER et MA_LISTE_PASSWORD sont à définir chez l'hébergeur (jamais dans ce fichier)
CMD ["python", "ma_liste.py"]
