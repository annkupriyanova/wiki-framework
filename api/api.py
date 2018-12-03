import mwclient as mw


site = mw.Site(('http', 'mediawiki:80'), path='/')
site.login('user', 'pass')
page = site.Pages['New']
text = page.text()
text += "* [[:" + 'New page' + "]]\n"

page.save(text, summary='Creating next page')
