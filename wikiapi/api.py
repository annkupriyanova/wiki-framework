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


