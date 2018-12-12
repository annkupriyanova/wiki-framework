import logging
import hashlib
import gettext
import locale
import os
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

from config import get_config
from term_collection import TermCollection
from database import POSEnum


# default language settings
locale_path = 'data/locale/'
language = gettext.translation('bot', locale_path, ['en'])
_ = language.gettext

# logging settings
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
logger = logging.getLogger(__name__)

# getting bot parameters from config file
params = get_config(section='bot')


def change_language(lang_code):
    """Changes language settings"""
    global language, options, _
    try:
        language = gettext.translation('bot', locale_path, [lang_code])
        _ = language.gettext
        options = set_options()
    except IOError:
        pass


def set_options():
    """Updates UI menu options"""
    return {
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

# set default english menu options
options = set_options()


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

    def set_keyboard(self):
        """Sets keyboard according to user's language. Default is English."""
        self.reply_start_menu_keyboard = ReplyKeyboardMarkup([[options['new_term']], [options['list_term']]],
                                                             resize_keyboard=True, one_time_keyboard=True)

        self.reply_menu_keyboard = ReplyKeyboardMarkup([[options['pos_tag'], options['description']],
                                                        [options['synonyms'], options['similars']],
                                                        [options['image'], options['audio'], options['video']]],
                                                       resize_keyboard=True)

    def update_state_handlers(self):
        """Adds Regular Expression Handlers according to user's language."""
        self.dispatcher.handlers[0][0].states[self.START_MENU].extend([
            RegexHandler(f"^{options['new_term']}$", self.new_term_option),
            RegexHandler(f"^{options['list_term']}$", self.list_of_terms_option)
        ])
        self.dispatcher.handlers[0][0].states[self.CHOOSE_OPTION].append(
            RegexHandler(f"^({options['pos_tag']}|{options['description']}|{options['synonyms']}|"
                         f"{options['similars']}|{options['image']}|{options['audio']}|{options['video']})$",
                         self.choose_menu_option)
        )

    def start(self, bot, update):
        """
        Sends the greeting message with the start menu: 'Add new term' and 'Get list of terms' options
        :return: the state START_MENU
        """
        # set language settings, UI-elements and button handlers according User's language_code
        lang_code = update.message.from_user.language_code
        if lang_code != 'en':
            change_language(lang_code)

        self.set_keyboard()
        self.update_state_handlers()

        update.message.reply_text(_('Hello! I am Terminology Bot. Send /cancel to stop talking to me.'),
                                  reply_markup=self.reply_start_menu_keyboard)
        return self.START_MENU

    def new_term_option(self, bot, update):
        """
        Callback function for the user choosing 'Add new term' option
        :return: the state NEW_TERM
        """
        update.message.reply_text(_('Type in the term.'))
        return self.NEW_TERM

    def add_new_term(self, bot, update):
        """
        Adds new term to DB from the user input
        :return: the state START_MENU
        """
        user = update.message.from_user
        term_name = update.message.text

        logger.info('User %s added the term "%s"', user.first_name, term_name)

        self.term_collection.create(term_name)

        update.message.reply_text(_('I\'ll remember this term.'), reply_markup=self.reply_start_menu_keyboard)

        return self.START_MENU

    def list_of_terms_option(self, bot, update):
        """
        Callback function for the user choosing 'Get list of terms' option.
        Sends the message with the list of terms from DB.
        :return: the state CHOOSE_TERM
        """
        terms = self.term_collection.get_terms()
        terms_list = [f'{i+1}. {terms[i]}' for i in range(len(terms))]

        text_list = [_('These are the terms I know:')]
        text_list.extend(terms_list)
        text_list.append(_('\nPlease, choose one of them.'))

        text = '\n'.join(text_list)

        update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

        return self.CHOOSE_TERM

    def choose_term(self, bot, update):
        """
        Sets the current term for future editing based on the user input
        :return: the state CHOOSE_OPTION
        """
        user = update.message.from_user
        try:
            index = int(update.message.text) - 1
            self.cur_term = self.term_collection[index]

            logger.info('User %s chose the term "%s"', user.first_name, self.cur_term.name)

            text = _('Let\'s make the profile of the term "%s".\n'
                     'Feel free to go back to the /menu and to the list of /terms.') % self.cur_term.name
            update.message.reply_text(text, reply_markup=self.reply_menu_keyboard)

            return self.CHOOSE_OPTION

        except (IndexError, ValueError):
            text = _('Please choose an index number of a term from the list above.')
            update.message.reply_text(text)
            return self.CHOOSE_TERM

    def choose_menu_option(self, bot, update):
        """
        Directs the user for futher actions based on the option he chose from the menu
        :return: the state depending on the user input
        """
        option = update.message.text
        if option == _('POS-tag'):
            reply_keyboard = [POSEnum.__members__.keys()]
            text = _('Choose the part-of-speech tag for the term "%s".') % self.cur_term.name

            update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                             one_time_keyboard=True,
                                                                             resize_keyboard=True))
            return self.POS

        elif option == _('Description'):
            text = _('Give a description to the term "%s".') % self.cur_term.name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.DESCRIPTION

        elif option == _('Synonyms'):
            text = _('List synonyms of the term "%s" separating them with comma.') % self.cur_term.name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.SYNONYMS

        elif option == _('Similar words'):
            text = _('List words similar with the term "%s" separating them with comma.') % self.cur_term.name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.SIMILARS

        elif option == _('Image'):
            text = _('Let\'s upload an image for the term "%s".') % self.cur_term.name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.IMAGE

        elif option == _('Audio'):
            text = _('Let\'s upload an audiofile for the term "%s".') % self.cur_term.name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.AUDIO

        elif option == _('Video'):
            text = _('Let\'s upload a video for the term "%s".') % self.cur_term.name
            update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return self.VIDEO

        else:
            text = _('Feel free to choose.')
            update.message.reply_text(text, reply_markup=self.reply_menu_keyboard)
            return self.CHOOSE_OPTION

    def pos_tag(self, bot, update):
        """
        Saves pos-tag of the current term to DB
        """
        user = update.message.from_user
        pos_tag = update.message.text

        logger.info('User %s chose pos-tag "%s"', user.first_name, pos_tag)

        self.term_collection.update(self.cur_term.id, {'pos_tag': pos_tag})

        update.message.reply_text(_('I see!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def description(self, bot, update):
        """
        Saves description of the current term to DB
        """
        user = update.message.from_user
        dscr = update.message.text

        logger.info('User %s gave a description to the term "%s"', user.first_name, self.cur_term.name)

        self.term_collection.update(self.cur_term.id, {'description': dscr})

        update.message.reply_text(_('Good work!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def image(self, bot, update):
        """
        Saves image of the current term to DB
        """
        user = update.message.from_user
        photo_file = bot.get_file(update.message.photo[-1].file_id)

        filename_sha1 = hashlib.sha1(bytes(f'image_{self.cur_term.name}', encoding='utf8')).hexdigest()

        directory = f"{params['multimedia_dir']}/images"
        if not os.path.exists(directory):
            os.makedirs(directory)
        photo_file.download(f"{directory}/{filename_sha1}.jpg")

        logger.info('User %s uploaded the image for the term "%s"', user.first_name, self.cur_term.name)

        self.term_collection.update(self.cur_term.id, {'image': f'image_{self.cur_term.name}'})

        update.message.reply_text(_('Awesome!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def audio(self, bot, update):
        """
        Saves audiofile of the current term to DB
        """
        user = update.message.from_user
        audio_file = bot.get_file(update.message.audio)

        filename_sha1 = hashlib.sha1(bytes(f'audio_{self.cur_term.name}', encoding='utf8')).hexdigest()

        directory = f"{params['multimedia_dir']}/audio"
        if not os.path.exists(directory):
            os.makedirs(directory)
        audio_file.download(f"{directory}/{filename_sha1}")

        logger.info('User %s uploaded the audiofile for the term "%s"', user.first_name, self.cur_term.name)

        self.term_collection.update(self.cur_term.id, {'audiofile': f'audio_{self.cur_term.name}'})

        update.message.reply_text(_('Awesome!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def video(self, bot, update):
        """
        Saves videofile of the current term to DB
        """
        user = update.message.from_user

        video_file = bot.get_file(update.message.video)

        filename_sha1 = hashlib.sha1(bytes(f'video_{self.cur_term.name}', encoding='utf8')).hexdigest()

        directory = f"{params['multimedia_dir']}/video"
        if not os.path.exists(directory):
            os.makedirs(directory)
        video_file.download(f"{directory}/{filename_sha1}")

        logger.info('User %s uploaded the videofile for the term "%s"', user.first_name, self.cur_term.name)

        self.term_collection.update(self.cur_term.id, {'videofile': f'video_{self.cur_term.name}'})

        update.message.reply_text(_('Awesome!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def synonyms(self, bot, update):
        """
        Saves synonyms of the current term to DB
        """
        user = update.message.from_user
        text = update.message.text

        synonyms = [syn.strip(' ') for syn in text.split(',')]

        logger.info('User %s listed synonyms for the term "%s"', user.first_name, self.cur_term.name)

        self.term_collection.add_synonyms_similars(self.cur_term.id, words=synonyms, table='syn')

        update.message.reply_text(_('I\'ll remember this!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def similars(self, bot, update):
        """
        Saves similar words of the current term to DB
        """
        user = update.message.from_user
        text = update.message.text

        similars = [sim.strip(' ') for sim in text.split(',')]

        logger.info('User %s listed similar words for the term "%s"', user.first_name, self.cur_term.name)

        self.term_collection.add_synonyms_similars(self.cur_term.id, words=similars, table='sim')

        update.message.reply_text(_('I\'ll remember this!'), reply_markup=self.reply_menu_keyboard)
        return self.CHOOSE_OPTION

    def error(self, bot, update, error):
        """
        Log Errors caused by Updates.
        """
        logger.warning('Update "%s" caused error "%s"', update, error)

    def cancel(self, bot, update):
        """
        Finishes the conversation after the user entered /cancel command
        """
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
            entry_points=[CommandHandler('start', self.start)],

            states={
                self.START_MENU: [],

                self.CHOOSE_TERM: [
                    RegexHandler('^[0-9]+$', self.choose_term),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.NEW_TERM: [
                    MessageHandler(Filters.text, self.add_new_term),
                    CommandHandler('start', self.start)
                ],

                self.CHOOSE_OPTION: [
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.POS: [
                    RegexHandler(f"^({'|'.join(tags)})$", self.pos_tag),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.DESCRIPTION: [
                    MessageHandler(Filters.text, self.description),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.SYNONYMS: [
                    MessageHandler(Filters.text, self.synonyms),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.SIMILARS: [
                    MessageHandler(Filters.text, self.similars),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.IMAGE: [
                    MessageHandler(Filters.photo, self.image),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.AUDIO: [
                    MessageHandler(Filters.audio, self.audio),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ],

                self.VIDEO: [
                    MessageHandler(Filters.video, self.video),
                    CommandHandler('menu', self.choose_menu_option),
                    CommandHandler('terms', self.list_of_terms_option),
                    CommandHandler('start', self.start)
                ]
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        self.dispatcher.add_handler(conv_handler)

        self.dispatcher.add_error_handler(self.error)

        self.updater.start_polling()

        self.updater.idle()

    # def get_term_profile(self):
    #     """
    #     Makes the short profile of the term chosen by the user.
    #     """
    #     profile = ''
    #     if self.cur_term.pos_tag:
    #         profile += f'1. {self.cur_term.pos_tag}\n'
    #     if self.cur_term.description:
    #         profile += f'2. {self.cur_term.description}\n'
    #
    #     return profile


if __name__ == '__main__':
    bot = Bot()
    bot.run()
