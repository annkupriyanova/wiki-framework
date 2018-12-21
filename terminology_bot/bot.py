import logging
import hashlib
import gettext
import os
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

from config import get_config
from term_collection import TermCollection
from database import POSEnum


# logging settings
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
logger = logging.getLogger(__name__)

# getting bot parameters from config file
params = get_config(section='bot')


class Bot:
    START_MENU, CHOOSE_TERM, NEW_TERM, CHOOSE_OPTION, \
    POS, DESCRIPTION, SYNONYMS, SIMILARS, IMAGE, AUDIO, VIDEO, CLARIFY_CHOICE = range(12)

    def __init__(self):
        self.updater = Updater(token=params['token'])
        self.dispatcher = self.updater.dispatcher
        self.term_collection = TermCollection()
        self.cur_term = {}

    def set_language_and_options(self, lang_code):
        """Sets language, UI-elements and button handlers according to lang_code"""
        locale_path = 'data/locale/'
        language = gettext.translation('bot', locale_path, ['en'])

        try:
            language = gettext.translation('bot', locale_path, [lang_code])
        except IOError:
            logger.info('No translation files for "%s" were found. English was set by default.', lang_code)
        finally:
            _ = language.gettext
            options = {
                'new_term': _('Add new term'),
                'list_term': _('Get list of terms'),
                'pos_tag': _('POS-tag'),
                'description': _('Description'),
                'synonyms': _('Synonyms'),
                'similars': _('Similar words'),
                'image': _('Image'),
                'audio': _('Audio'),
                'video': _('Video'),
            }
            pos_tags = {_(member.value): member.value for name, member in POSEnum.__members__.items()}

            start_btn, term_btn, pos_btn = self.set_keyboard(options, pos_tags.keys())
            self.update_state_handlers(options, pos_tags.keys())

            return language, options, pos_tags, start_btn, term_btn, pos_btn

    def set_keyboard(self, options, tags):
        """Sets keyboard according to user's language. Default is English."""
        start_btn = [[options['new_term']], [options['list_term']]]
        term_btn = [[options['pos_tag'], options['description']],
                    [options['synonyms'], options['similars']],
                    [options['image'], options['audio'], options['video']]]
        pos_btn = [tags]
        return start_btn, term_btn, pos_btn

    def update_state_handlers(self, options, tags):
        """Adds Regular Expression Handlers according to user's language."""
        self.dispatcher.handlers[0][0].states[self.START_MENU].extend([
            RegexHandler(f"^{options['new_term']}$", self.new_term_option, pass_user_data=True),
            RegexHandler(f"^{options['list_term']}$", self.list_of_terms_option, pass_user_data=True)
        ])
        self.dispatcher.handlers[0][0].states[self.CHOOSE_OPTION].append(
            RegexHandler(f"^({options['pos_tag']}|{options['description']}|{options['synonyms']}|"
                         f"{options['similars']}|{options['image']}|{options['audio']}|{options['video']})$",
                         self.choose_menu_option, pass_user_data=True)
        )
        self.dispatcher.handlers[0][0].states[self.POS].append(
            RegexHandler(f"^({'|'.join(tags)})$", self.pos_tag, pass_user_data=True)
        )

    def start(self, bot, update, user_data):
        """
        Sends the greeting message with the start menu: 'Add new term' and 'Get list of terms' options
        :return: the state START_MENU
        """
        lang_code = update.message.from_user.language_code
        lang, options, pos_tags, start_btn, term_btn, pos_btn = self.set_language_and_options(lang_code)
        user_data.update({'lang': lang, 'options': options, 'pos_tags': pos_tags,
                          'start_btn': start_btn, 'term_btn': term_btn, 'pos_btn': pos_btn})

        _ = user_data['lang'].gettext
        update.message.reply_text(_('Hello! I am Terminology Bot. Send /cancel to stop talking to me.'),
                                  reply_markup=ReplyKeyboardMarkup(keyboard=user_data['start_btn'],
                                                                   resize_keyboard=True, one_time_keyboard=True))
        return self.START_MENU

    def new_term_option(self, bot, update, user_data):
        """
        Callback function for the user choosing 'Add new term' option
        :return: the state NEW_TERM
        """
        _ = user_data['lang'].gettext
        update.message.reply_text(_('Type in the term.'))
        return self.NEW_TERM

    def add_new_term(self, bot, update, user_data):
        """
        Adds new term to DB from the user input
        :return: the state START_MENU
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        term_name = update.message.text

        logger.info('User %s added the term "%s"', user.first_name, term_name)

        self.term_collection.create(term_name)

        update.message.reply_text(_('I\'ll remember this term.'), reply_markup=ReplyKeyboardMarkup(
            keyboard=user_data['start_btn'], resize_keyboard=True, one_time_keyboard=True))

        return self.START_MENU

    def list_of_terms_option(self, bot, update, user_data):
        """
        Callback function for the user choosing 'Get list of terms' option.
        Sends the message with the list of terms from DB.
        :return: the state CHOOSE_TERM
        """
        _ = user_data['lang'].gettext

        terms = self.term_collection.get_terms()
        user_data['terms'] = {i+1: terms[i] for i in range(len(terms))}
        terms_list = [f'{key}. {term.name} {"(" + term.pos_tag.value + ")" if term.pos_tag else ""}'
                      for key, term in user_data['terms'].items()]

        text_list = [_('These are the terms I know:')]
        text_list.extend(terms_list)
        text_list.append(_('\nPlease, choose one of them.'))

        text = '\n'.join(text_list)

        update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

        return self.CHOOSE_TERM

    def choose_term(self, bot, update, user_data):
        """
        Sets the current term for future editing based on the user input
        :return: the state CHOOSE_OPTION
        """
        _ = user_data['lang'].gettext
        user = update.message.from_user
        try:
            index = int(update.message.text)
            id = user_data['terms'][index].id
            user_data['cur_term'] = self.term_collection.get(id)

            del user_data['terms']

            logger.info('User %s chose the term "%s"', user.first_name, user_data['cur_term'].name)

            _ = user_data['lang'].gettext

            term_pos = ''
            term_descr = ''
            if user_data['cur_term'].pos_tag:
                term_pos = f"({_(user_data['cur_term'].pos_tag.value)})"
            if user_data['cur_term'].description:
                term_descr = f": {user_data['cur_term'].description}"

            text = _('Let\'s make the profile of the term "%s" %s%s.\n'
                     'Feel free to go back to the /menu and to the list of /terms.\n') % (user_data['cur_term'].name,
                                                                                          term_pos, term_descr)
            update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                             resize_keyboard=True))

            return self.CHOOSE_OPTION

        except (IndexError, ValueError):
            text = _('Please choose an index number of a term from the list above.')
            update.message.reply_text(text)
            return self.CHOOSE_TERM

    def choose_menu_option(self, bot, update, user_data):
        """
        Directs the user for futher actions based on the option he chose from the menu
        :return: the state depending on the user input
        """
        _ = user_data['lang'].gettext

        option = update.message.text
        if option == _('POS-tag'):
            text = _('Choose the part-of-speech tag for the term "%s".') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(user_data['pos_btn'],
                                                                             one_time_keyboard=True,
                                                                             resize_keyboard=True))
            return self.POS

        elif option == _('Description'):
            text = _('Give a description to the term "%s".') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.DESCRIPTION

        elif option == _('Synonyms'):
            text = _('List synonyms of the term "%s" separating them with comma.') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.SYNONYMS

        elif option == _('Similar words'):
            text = _('List words similar with the term "%s" separating them with comma.') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.SIMILARS

        elif option == _('Image'):
            text = _('Let\'s upload an image for the term "%s".') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.IMAGE

        elif option == _('Audio'):
            text = _('Let\'s upload an audiofile for the term "%s".') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.AUDIO

        elif option == _('Video'):
            text = _('Let\'s upload a video for the term "%s".') % user_data['cur_term'].name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.VIDEO

        else:
            text = _('Feel free to choose.')
            update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                             resize_keyboard=True))
            return self.CHOOSE_OPTION

    def pos_tag(self, bot, update, user_data):
        """
        Saves pos-tag of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        pos_tag = update.message.text
        original_pos_tag = user_data['pos_tags'][pos_tag]

        logger.info('User %s chose pos-tag "%s"', user.first_name, original_pos_tag)

        self.term_collection.update(user_data['cur_term'].id, {'pos_tag': original_pos_tag})

        update.message.reply_text(_('I see!'), reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                                resize_keyboard=True))
        return self.CHOOSE_OPTION

    def description(self, bot, update, user_data):
        """
        Saves description of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        dscr = update.message.text

        logger.info('User %s gave a description to the term "%s"', user.first_name, user_data['cur_term'].name)

        self.term_collection.update(user_data['cur_term'].id, {'description': dscr})

        update.message.reply_text(_('Good work!'), reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                                    resize_keyboard=True))
        return self.CHOOSE_OPTION

    def image(self, bot, update, user_data):
        """
        Saves image of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        photo_file = bot.get_file(update.message.photo[-1].file_id)

        filename_sha1 = hashlib.sha1(bytes(f"image_{user_data['cur_term'].id}", encoding='utf8')).hexdigest()

        directory = f"{params['multimedia_dir']}/images"
        if not os.path.exists(directory):
            os.makedirs(directory)
        photo_file.download(f"{directory}/{filename_sha1}.jpg")

        logger.info('User %s uploaded the image for the term "%s"', user.first_name, user_data['cur_term'].name)

        self.term_collection.update(user_data['cur_term'].id, {'image': f"image_{user_data['cur_term'].id}"})

        update.message.reply_text(_('Awesome!'), reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                                  resize_keyboard=True))
        return self.CHOOSE_OPTION

    def audio(self, bot, update, user_data):
        """
        Saves audiofile of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        if update.message.audio:
            audio_file = bot.get_file(update.message.audio)
        elif update.message.voice:
            audio_file = bot.get_file(update.message.voice)
            print(audio_file)

        filename_sha1 = hashlib.sha1(bytes(f"audio_{user_data['cur_term'].id}", encoding='utf8')).hexdigest()

        directory = f"{params['multimedia_dir']}/audio"
        if not os.path.exists(directory):
            os.makedirs(directory)
        audio_file.download(f"{directory}/{filename_sha1}")

        logger.info('User %s uploaded the audiofile for the term "%s"', user.first_name, user_data['cur_term'].name)

        self.term_collection.update(user_data['cur_term'].id, {'audiofile': f"audio_{user_data['cur_term'].id}"})

        update.message.reply_text(_('Awesome!'), reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                                  resize_keyboard=True))
        return self.CHOOSE_OPTION

    def video(self, bot, update, user_data):
        """
        Saves videofile of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user

        video_file = bot.get_file(update.message.video)

        filename_sha1 = hashlib.sha1(bytes(f"video_{user_data['cur_term'].id}", encoding='utf8')).hexdigest()

        directory = f"{params['multimedia_dir']}/video"
        if not os.path.exists(directory):
            os.makedirs(directory)
        video_file.download(f"{directory}/{filename_sha1}")

        logger.info('User %s uploaded the videofile for the term "%s"', user.first_name, user_data['cur_term'].name)

        self.term_collection.update(user_data['cur_term'].id, {'videofile': f"video_{user_data['cur_term'].id}"})

        update.message.reply_text(_('Awesome!'), reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                                  resize_keyboard=True))
        return self.CHOOSE_OPTION

    def synonyms(self, bot, update, user_data):
        """
        Saves synonyms of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        text = update.message.text

        synonyms = [syn.strip(' ') for syn in text.split(',')]

        logger.info('User %s listed synonyms for the term "%s"', user.first_name, user_data['cur_term'].name)

        result = self.term_collection.add_synonyms_similars(user_data['cur_term'].id, words=synonyms, table='synonyms')

        if not result:
            # DB transaction was successful
            update.message.reply_text(_('I\'ll remember this!'), reply_markup=ReplyKeyboardMarkup(
                keyboard=user_data['term_btn'], resize_keyboard=True))
            return self.CHOOSE_OPTION

        else:
            user_data['s_words_list'] = result
            user_data['option'] = 'synonyms'
            terms_list = self.get_clarification_list(result, _)

            update.message.reply_text(_('List indices of the terms you meant, separating them with comma:\n%s')
                                      % '\n'.join(terms_list),
                                      reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                       resize_keyboard=True))
            return self.CLARIFY_CHOICE

    def similars(self, bot, update, user_data):
        """
        Saves similar words of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        text = update.message.text

        similars = [sim.strip(' ') for sim in text.split(',')]

        logger.info('User %s listed similar words for the term "%s"', user.first_name, user_data['cur_term'].name)

        result = self.term_collection.add_synonyms_similars(user_data['cur_term'].id, words=similars, table='similars')

        if not result:
            # DB transaction was successful
            update.message.reply_text(_('I\'ll remember this!'), reply_markup=ReplyKeyboardMarkup(
                keyboard=user_data['term_btn'], resize_keyboard=True))
            return self.CHOOSE_OPTION
        else:
            user_data['s_words_list'] = result
            user_data['option'] = 'similars'
            terms_list = self.get_clarification_list(result, _)

            update.message.reply_text(_('List indices of the terms you meant, separating them with comma:\n%s')
                                      % '\n'.join(terms_list), reply_markup=ReplyKeyboardMarkup(keyboard=user_data['term_btn'],
                                                                                     resize_keyboard=True))
            return self.CLARIFY_CHOICE

    def get_clarification_list(self, result, _):
        terms_list = []
        for i, t in enumerate(result):
            line = f'{i+1}. {t.name}'
            if t.pos_tag:
                line += f' ({_(t.pos_tag.value)})'
            if t.description:
                line += f': {t.description}'
            terms_list.append(line)
        return terms_list

    def clarify_choice(self, bot, update, user_data):
        _ = user_data['lang'].gettext
        user = update.message.from_user
        text = update.message.text

        try:
            indices = [int(i) - 1 for i in text.split(',')]
            clarification_ids = []

            for index in indices:
                s_word = user_data['s_words_list'][index]
                clarification_ids.append(s_word.id)

            logger.info('User %s clarified the terms.', user.first_name)

            self.term_collection.add_synonyms_similars(user_data['cur_term'].id, [], table=user_data['option'],
                                                       clarification_ids=clarification_ids)
            del user_data['s_words_list']
            del user_data['option']

            update.message.reply_text(_('I will save your choice.'), reply_markup=ReplyKeyboardMarkup(
                keyboard=user_data['term_btn'], resize_keyboard=True))
            return self.CHOOSE_OPTION

        except (IndexError, ValueError):
            text = _('Please choose an index number of a term from the list above.')
            update.message.reply_text(text)
            return self.CLARIFY_CHOICE

    def error(self, bot, update, error):
        """
        Log Errors caused by Updates.
        """
        logger.warning('Update "%s" caused error "%s"', update, error)

    def cancel(self, bot, update, user_data):
        """
        Finishes the conversation after the user entered /cancel command
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user

        logger.info('User %s canceled the conversation.', user.first_name)

        update.message.reply_text(_('Bye! I hope we can talk again some day.'),
                                  reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def run(self):
        """
        Registers the handlers of user actions and starts the bot
        """
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start, pass_user_data=True)],

            states={
                self.START_MENU: [],

                self.CHOOSE_TERM: [
                    RegexHandler('^[0-9]+$', self.choose_term, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.CLARIFY_CHOICE: [
                    MessageHandler(Filters.text, self.clarify_choice, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.NEW_TERM: [
                    MessageHandler(Filters.text, self.add_new_term, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.CHOOSE_OPTION: [
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.POS: [
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.DESCRIPTION: [
                    MessageHandler(Filters.text, self.description, pass_user_data=True),
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.SYNONYMS: [
                    MessageHandler(Filters.text, self.synonyms, pass_user_data=True),
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.SIMILARS: [
                    MessageHandler(Filters.text, self.similars, pass_user_data=True),
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.IMAGE: [
                    MessageHandler(Filters.photo, self.image, pass_user_data=True),
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.AUDIO: [
                    MessageHandler(Filters.audio | Filters.voice, self.audio, pass_user_data=True),
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ],

                self.VIDEO: [
                    MessageHandler(Filters.video, self.video, pass_user_data=True),
                    CommandHandler('menu', self.choose_menu_option, pass_user_data=True),
                    CommandHandler('terms', self.list_of_terms_option, pass_user_data=True),
                    CommandHandler('start', self.start, pass_user_data=True)
                ]
            },

            fallbacks=[CommandHandler('cancel', self.cancel, pass_user_data=True)]
        )

        self.dispatcher.add_handler(conv_handler)

        self.dispatcher.add_error_handler(self.error)

        self.updater.start_polling()

        self.updater.idle()


if __name__ == '__main__':
    bot = Bot()
    bot.run()
