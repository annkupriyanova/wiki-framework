from sqlalchemy import (create_engine, Column, String, Integer, Text, Enum, ForeignKey, Sequence)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_config
import enum


Base = declarative_base()

params = get_config(section='postgresql')
db_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}/{params['database']}"


class POSEnum(enum.Enum):
    noun = 'noun'
    verb = 'verb'
    adjective = 'adjective'


class Term(Base):
    __tablename__ = 'terms'

    id = Column(Integer, Sequence('terms_id_seq'), primary_key=True)
    name = Column(String(256), nullable=False, unique=True)
    pos_tag = Column(Enum(POSEnum))
    description = Column(Text)
    image = Column(String(256))
    audiofile = Column(String(256))
    videofile = Column(String(256))

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)


class Synonyms(Base):
    __tablename__ = 'synonyms'

    term_id = Column(Integer, ForeignKey(Term.id), primary_key=True)
    synonym_id = Column(Integer, ForeignKey(Term.id), primary_key=True)


class Similars(Base):
    __tablename__ = 'similar_words'

    term_id = Column(Integer, ForeignKey(Term.id), primary_key=True)
    similar_word_id = Column(Integer, ForeignKey(Term.id), primary_key=True)


class SQLAlchemyDBConnection(object):
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.session = None

    def __enter__(self):
        engine = create_engine(self.connection_string)
        Session = sessionmaker()
        self.session = Session(bind=engine)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


def create_tables():
    """
    Creates the DB schema based on the classes Term, Synonyms, Similars
    """
    engine = create_engine(db_string)
    Base.metadata.create_all(engine)


def seed_tables():
    """
    Inserts Term instances into DB
    """
    terms = [
        Term(name='juba'),
        Term(name='fixation'),
        Term(name='valet'),
        Term(name='wallet'),
        Term(name='hydrocolloid'),
    ]

    with SQLAlchemyDBConnection(db_string) as db:
        db.session.add_all(terms)
        db.session.commit()

    print('Terminology database is ready.')


if __name__ == '__main__':
    create_tables()
    seed_tables()
