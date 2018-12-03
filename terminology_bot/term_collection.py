from database import (SQLAlchemyDBConnection, Term, Synonyms, Similars, db_string)
from sqlalchemy import exists


class TermCollection:
    def __init__(self):
        self.terms = []

    def get_terms(self):
        with SQLAlchemyDBConnection(db_string) as db:
            self.terms = [t.name for t in db.session.query(Term)]
        return self.terms

    def create(self, term_name):
        term_name = term_name.lower()

        with SQLAlchemyDBConnection(db_string) as db:
            term_exists = db.session.query(exists().where(Term.name == term_name)).scalar()
            if not term_exists:
                db.session.add(Term(name=term_name))
                db.session.commit()

    def update(self, term_id, dictionary):
        with SQLAlchemyDBConnection(db_string) as db:
            term = db.session.query(Term).filter(Term.id == term_id).first()

            for key, val in dictionary.items():
                term[key] = val

            db.session.commit()

    def add_synonyms_similars(self, term_id, words, table='syn'):
        with SQLAlchemyDBConnection(db_string) as db:
            term = db.session.query(Term).filter(Term.id == term_id).first()
            words = [w.lower() for w in words]

            for word in words:
                word_exists = db.session.query(exists().where(Term.name == word)).scalar()

                if not word_exists:
                    db.session.add(Term(name=word))
                    db.session.flush()

                s_word = db.session.query(Term).filter(Term.name == word).first()

                if table == 'syn':
                    db.session.add(Synonyms(term_id=term.id, synonym_id=s_word.id))
                elif table == 'sim':
                    db.session.add(Similars(term_id=term.id, similar_word_id=s_word.id))

            db.session.commit()

    def __getitem__(self, index):
        name = self.terms[index]

        with SQLAlchemyDBConnection(db_string) as db:
            term = db.session.query(Term).filter(Term.name == name).first()

        return term
