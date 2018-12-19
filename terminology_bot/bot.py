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


# default language settings
# locale_path = 'data/locale/'
# language = gettext.translation('bot', locale_path, ['en'])
# _ = language.gettext

# logging settings
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
logger = logging.getLogger(__name__)

# getting bot parameters from config file
params = get_config(section='bot')


class Bot:
    START_MENU, CHOOSE_TERM, NEW_TERM, CHOOSE_OPTION, \
    POS, DESCRIPTION, SYNONYMS, SIMILARS, IMAGE, AUDIO, VIDEO = range(11)

    reply_start_menu_keyboard = ReplyKeyboardMarkup([])
    reply_menu_keyboard = ReplyKeyboardMarkup([])

    def __init__(self):
        self.updater = Updater(token=params['token'])
        self.dispatcher = self.updater.dispatcher
        self.term_collection = TermCollection()
        self.cur_term = {}

    def set_language_and_options(self, lang_code):
        locale_path = 'data/locale/'
        language = gettext.translation('bot', locale_path, ['en'])

        try:
            language = gettext.translation('bot', locale_path, [lang_code])
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
            self.set_keyboard(options)
            self.update_state_handlers(options)
            start_btn, term_btn = self.set_keyboard(options)

            return language, options, start_btn, term_btn

    def set_keyboard(self, options):
        """Sets keyboard according to user's language. Default is English."""
        start_btn = [[options['new_term']], [options['list_term']]]
        term_btn = [[options['pos_tag'], options['description']],
                    [options['synonyms'], options['similars']],
                    [options['image'], options['audio'], options['video']]]
        return start_btn, term_btn

    def update_state_handlers(self, options):
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

    def start(self, bot, update, user_data):
        """
        Sends the greeting message with the start menu: 'Add new term' and 'Get list of terms' options
        :return: the state START_MENU
        """
        # set language settings, UI-elements and button handlers according User's language_code
        lang_code = update.message.from_user.language_code
        print(update.message.from_user.first_name, lang_code)
        lang, options, start_btn, term_btn = self.set_language_and_options(lang_code)
        user_data.update({'lang': lang, 'options': options, 'start_btn': start_btn, 'term_btn': term_btn})

        _ = user_data['lang'].gettext
        update.message.reply_text(_('Hello! I am Terminology Bot. Send /cancel to stop talking to me.'),
                                  reply_markup=self.reply_start_menu_keyboard)
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
        terms_list = [f'{key}. {term.name}' for key, term in user_data['terms'].items()]

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

            text = _('Let\'s make the profile of the term "%s".\n'
                     'Feel free to go back to the /menu and to the list of /terms.') % user_data['cur_term'].name
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
            reply_keyboard = [POSEnum.__members__.keys()]
            text = _('Choose the part-of-speech tag for the term "%s".') % user_data['cur_term'].name

            update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(reply_keyboard,
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

        logger.info('User %s chose pos-tag "%s"', user.first_name, pos_tag)

        self.term_collection.update(user_data['cur_term'].id, {'pos_tag': pos_tag})

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

        self.term_collection.add_synonyms_similars(user_data['cur_term'].id, words=synonyms, table='syn')

        update.message.reply_text(_('I\'ll remember this!'), reply_markup=ReplyKeyboardMarkup(
            keyboard=user_data['term_btn'], resize_keyboard=True))
        return self.CHOOSE_OPTION

    def similars(self, bot, update, user_data):
        """
        Saves similar words of the current term to DB
        """
        _ = user_data['lang'].gettext

        user = update.message.from_user
        text = update.message.text

        similars = [sim.strip(' ') for sim in text.split(',')]

        logger.info('User %s listed similar words for the term "%s"', user.first_name, user_data['cur_term'].name)

        self.term_collection.add_synonyms_similars(user_data['cur_term'].id, words=similars, table='sim')

        update.message.reply_text(_('I\'ll remember this!'), reply_markup=ReplyKeyboardMarkup(
            keyboard=user_data['term_btn'], resize_keyboard=True))
        return self.CHOOSE_OPTION

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
        tags = POSEnum.__members__.keys()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start, pass_user_data=True)],

            states={
                self.START_MENU: [],

                self.CHOOSE_TERM: [
                    RegexHandler('^[0-9]+$', self.choose_term, pass_user_data=True),
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
                    RegexHandler(f"^({'|'.join(tags)})$", self.pos_tag, pass_user_data=True),
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
