docker run --rm -p 5555:5432 --name pg_terminology -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=admin -e POSTGRES_DB=terminology -d postgres
sleep 10
pip3 install -r requirements.txt
export PYTHONPATH=`pwd`
python3 database.py