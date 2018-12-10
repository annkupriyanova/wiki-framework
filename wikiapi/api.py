import mwclient as mw


site = mw.Site(('http', 'mediawiki:80'), path='/')
site.login('user', 'pass')
page = site.Pages['Galileo']
text = ''
with open('Galileo_page.txt', 'r') as f:
    for i in f.readlines():
        text += i


page.save(text, summary='Creating new Galileo page')
