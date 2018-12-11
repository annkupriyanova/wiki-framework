from .service import get_site, upload, make_text


def new_page(pagename, attributes):
    site = get_site()
    page = site.Pages[f'{pagename}']
    text = make_text(pagename, attributes)
    page.save(text, summary='Creating a new page')


def update_sections(page, attributes):
    site = get_site()
    page = site.Pages[f'{page}']
    for section, value in attributes.items():
        text = page.text(section=section)
        # some actions? uploading files
        text = value
        page.save(value, section=section)


def get_section(page, section):
    site = get_site()
    page = site.Pages[f'{page}']
    return page.text(section=section)


=======
import mwclient as mw


site = mw.Site(('http', 'mediawiki:80'), path='/')
site.login('user', 'pass')
page = site.Pages['Galileo']
text = ''
with open('Galileo_page.txt', 'r') as f:
    for i in f.readlines():
        text += i


page.save(text, summary='Creating new Galileo page')
>>>>>>> c7659997ae814b4680296461cb7c512fee47fa92
