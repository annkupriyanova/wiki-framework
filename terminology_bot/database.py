from sqlalchemy import (create_engine, Column, String, Integer, Text, Enum, ForeignKey, Sequence, Table)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_config
import enum


Base = declarative_base()

params = get_config(section='postgresql')
db_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}/{params['database']}"


# dummy function for gettext to recognize POSenum values
def _(str):
    return str


class POSEnum(enum.Enum):
    noun = _('noun')
    verb = _('verb')
    adjective = _('adjective')


Synonyms = Table('synonyms', Base.metadata,
                 Column('term_id', Integer, ForeignKey('terms.id'), primary_key=True),
                 Column('synonym_id', Integer, ForeignKey('terms.id'), primary_key=True))


Similars = Table('similar_words', Base.metadata,
                 Column('term_id', Integer, ForeignKey('terms.id'), primary_key=True),
                 Column('similar_word_id', Integer, ForeignKey('terms.id'), primary_key=True))


class Term(Base):
    __tablename__ = 'terms'

    id = Column(Integer, Sequence('terms_id_seq'), primary_key=True)
    name = Column(String(256), nullable=False)
    pos_tag = Column(Enum(POSEnum))
    description = Column(Text)
    image = Column(String(256))
    audiofile = Column(String(256))
    videofile = Column(String(256))

    synonyms = relationship("Term", secondary=Synonyms,
                            primaryjoin=Synonyms.c.term_id == id,
                            secondaryjoin=Synonyms.c.synonym_id == id)

    similars = relationship("Term", secondary=Similars,
                            primaryjoin=Similars.c.term_id == id,
                            secondaryjoin=Similars.c.similar_word_id == id)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)


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
