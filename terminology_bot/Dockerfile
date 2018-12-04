
FROM ubuntu

RUN apt-get update && apt-get install -y gnupg apt-utils

RUN apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN apt-get update && apt-get install -y postgresql postgresql-contrib

USER postgres

RUN echo "host all  all   0.0.0.0/0  password" >> /etc/postgresql/10/main/pg_hba.conf

RUN /etc/init.d/postgresql start && psql --command "CREATE USER admin WITH SUPERUSER PASSWORD 'admin';" && createdb terminology -O admin

RUN echo "listen_addresses='*'" >> /etc/postgresql/10/main/postgresql.conf

EXPOSE 5432

VOLUME  ["/etc/postgresql", "/var/log/postgresql", "/var/lib/postgresql"]

CMD ["/usr/lib/postgresql/10/bin/postgres", "-D", "/var/lib/postgresql/10/main", "-c", "config_file=/etc/postgresql/10/main/postgresql.conf"]
