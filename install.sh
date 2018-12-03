docker kill pg_terminology
docker rm /pg_terminology
docker build -t eg_postgresql .
docker run -p 5555:5432 -d --name pg_terminology eg_postgresql
sleep 10
pip3 install -r requirements.txt
export PYTHONPATH=`pwd`
python3 terminology_bot/database.py
docker attach pg_terminology