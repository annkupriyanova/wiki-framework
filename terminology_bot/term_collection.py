from database import (SQLAlchemyDBConnection, Term, Synonyms, Similars, db_string)
from sqlalchemy import exists


class TermCollection:
    def __init__(self):
        self.terms = []

    def get_terms(self):
        with SQLAlchemyDBConnection(db_string) as db:
            terms = db.session.query(Term).all()
        return terms

    def get(self, term_id):
        with SQLAlchemyDBConnection(db_string) as db:
            term = db.session.query(Term).filter(Term.id == term_id).first()
        return term

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
                if term[key] and term[key] != val:
                    new_term = Term(name=term.name)
                    new_term[key] = val
                    db.session.add(new_term)
                else:
                    term[key] = val

            db.session.commit()

    def add_synonyms_similars(self, term_id, words, table='synonyms', clarification_ids=None):
        s_words_to_clarify = []

        with SQLAlchemyDBConnection(db_string) as db:
            db.session.expire_on_commit = False

            term = db.session.query(Term).filter(Term.id == term_id).first()

            if clarification_ids:
                # this will be executed after user's clarification choice (in case of several s_words found in DB)
                for s_word_id in clarification_ids:
                    s_word = db.session.query(Term).filter(Term.id == s_word_id).first()
                    if table == 'synonyms':
                        term.synonyms.append(s_word)
                        s_word.synonyms.append(term)

                    elif table == 'similars':
                        term.similars.append(s_word)
                        s_word.similars.append(term)
            else:
                words = [w.lower() for w in words]

                for word in words:
                    word_exists = db.session.query(exists().where(Term.name == word)).scalar()

                    if not word_exists:
                        db.session.add(Term(name=word))
                        db.session.flush()

                    s_word_list = db.session.query(Term).filter(Term.name == word).all()

                    if len(s_word_list) > 1:
                        s_words_to_clarify.extend(s_word_list)
                    else:
                        if table == 'synonyms':
                            term.synonyms.append(s_word_list[0])
                            s_word_list[0].synonyms.append(term)

                        elif table == 'similars':
                            term.similars.append(s_word_list[0])
                            s_word_list[0].similars.append(term)

            db.session.commit()

        if s_words_to_clarify:
            # return list of s_words  for user's clarification choice
            return s_words_to_clarify
        else:
            return None

    def get_synonyms(self, term_id):
        with SQLAlchemyDBConnection(db_string) as db:
            db.session.expire_on_commit = False
            term = db.session.query(Term).filter(Term.id == term_id).first()
            return term.synonyms

    def get_similars(self, term_id):
        with SQLAlchemyDBConnection(db_string) as db:
            db.session.expire_on_commit = False
            term = db.session.query(Term).filter(Term.id == term_id).first()
            return term.similars
