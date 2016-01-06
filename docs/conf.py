
import sys
import os

extensions = [
    'sphinx.ext.todo',
]

source_suffix = '.txt'

master_doc = 'index'

### part to update ###################################
project = u'domogik-plugin-vdevice'
copyright = u'2015, domos'
version = '0.1'
release = version
######################################################

pygments_style = 'sphinx'

html_theme = 'default'
html_static_path = ['_static']
