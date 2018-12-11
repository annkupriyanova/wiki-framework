import mwclient as mw


def get_site():
    site = mw.Site(('http', 'mediawiki:80'), path='/')
    site.login('user', 'pass')
    return site


def upload(file, filename=None, description=None):
    site = get_site()
    if filename is None:
        filename = file
    with open(file, 'rb') as f:
        site.upload(f, filename=filename, description=description)


def make_text(pagename, attributes):
    section_order = {0: 'Description', 1: 'Part of speech', 2: 'Synonyms',
                     3: 'Similar words', 4: 'Photo', 5: 'Audio',
                     6: 'Video'}
    media_info = False
    additional_info = False
    for key, val in attributes.items():
        if key in ['audio', 'photo', 'video']:
            media_info = True
        if key in ['synonyms', 'similar_words']:
            additional_info = True

    text = f'**{pagename}**\n'
    for i in range(4):
        sec = section_order[i]
        if sec in attributes:
            text += f'=={sec}==\n'
            text += f'{attributes[sec]}\n'

    if media_info:
        text += '==Media==\n'
        for i in range(4, 7):
            sec = section_order[i]
            if sec in attributes:
                text += f'==={sec}===\n'
                upload(attributes[sec]['filename'])
                text += f'[[File:{attributes[sec]["filename"]}|' \
                        f'{attributes[sec]["description"]}]]\n'
    return text

