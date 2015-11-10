""" 
Based on Premailer.

This is a hack of Premailer that uses BeautifulSoup and SoupSelect instead of lxml.
"""
# http://www.peterbe.com/plog/premailer.py
import re, os
import codecs
import urlparse, urllib
from BeautifulSoup import BeautifulSoup, Comment
import soupselect; soupselect.monkeypatch()

__version__ = '1.9'

__all__ = ['PremailerError', 'Premailer', 'transform']

class PremailerError(Exception):
    pass

def _merge_styles(old, new, class_=''):
    """
    if ::
      old = 'font-size:1px; color: red'
    and ::
      new = 'font-size:2px; font-weight: bold'
    then ::
      return 'color: red; font-size:2px; font-weight: bold'
      
    In other words, the new style bits replace the old ones.
    
    The @class_ parameter can be something like ':hover' and if that
    is there, you split up the style with '{...} :hover{...}'
    Note: old could be something like '{...} ::first-letter{...}'
    
    """
    news = {}
    for k, v in [x.strip().split(':', 1) for x in new.split(';') if x.strip()]:
        news[k.strip()] = v.strip()

    groups = {}
    grouping_regex = re.compile('([:\-\w]*){([^}]+)}')
    grouped_split = grouping_regex.findall(old)
    if grouped_split:
        for old_class, old_content in grouped_split:
            olds = {}
            for k, v in [x.strip().split(':', 1) for x in old_content.split(';') if x.strip()]:
                olds[k.strip()] = v.strip()
            groups[old_class] = olds
    else:
        olds = {}
        for k, v in [x.strip().split(':', 1) for x in old.split(';') if x.strip()]:
            olds[k.strip()] = v.strip()
        groups[''] = olds
            
    # Perform the merge
    
    merged = news
    for k, v in groups.get(class_, {}).items():
        if k not in merged:
            merged[k] = v
    groups[class_] = merged
    
    if len(groups) == 1:
        return '; '.join(['%s:%s' % (k, v) for (k, v) in groups.values()[0].items()])
    else:
        all = []
        for class_, mergeable in sorted(groups.items(),
                                        lambda x, y: cmp(x[0].count(':'), y[0].count(':'))):
            all.append('%s{%s}' % (class_,
                                   '; '.join(['%s:%s' % (k, v) 
                                              for (k, v) 
                                              in mergeable.items()])))
        return ' '.join([x for x in all if x != '{}'])


_css_comments = re.compile(r'/\*.*?\*/', re.MULTILINE|re.DOTALL)
_regex = re.compile('((.*?){(.*?)})', re.DOTALL|re.M)
_semicolon_regex = re.compile(';(\s+)')
_colon_regex = re.compile(':(\s+)')


class Premailer(object):
    
    def __init__(self, html, base_url=None,
                 exclude_pseudoclasses=False,
                 keep_style_tags=False,
                 include_star_selectors=False,
                 external_styles=None):
        self.html = html
        self.base_url = base_url
        self.exclude_pseudoclasses = exclude_pseudoclasses
        # whether to delete the <style> tag once it's been processed
        self.keep_style_tags = keep_style_tags
        # whether to process or ignore selectors like '* { foo:bar; }'
        self.include_star_selectors = include_star_selectors
        if isinstance(external_styles, basestring):
            external_styles = [external_styles]
        self.external_styles = external_styles
        
    def _parse_style_rules(self, css_body):
        leftover = []
        rules = []        
        css_body = _css_comments.sub('', css_body)
        for each in _regex.findall(css_body.strip()):
            __, selectors, bulk = each

            bulk = _semicolon_regex.sub(';', bulk.strip())
            bulk = _colon_regex.sub(':', bulk.strip())
            if bulk.endswith(';'):
                bulk = bulk[:-1]
            for selector in [x.strip() for x in selectors.split(',') if x.strip()]:
                if ':' in selector and self.exclude_pseudoclasses:
                    # a pseudoclass
                    leftover.append((selector, bulk))
                    continue
                elif selector == '*' and not self.include_star_selectors:
                    continue
                
                rules.append((selector, bulk))

        return rules, leftover
        
    def transform(self):
        """change the self.html and return it with CSS turned into style
        attributes.
        """
        page = BeautifulSoup(self.html)

        if page is None:
            print repr(self.html)
            raise PremailerError("Could not parse the html")

        # Strip comments.
        comments = page.findAll(text=lambda text: isinstance(text, Comment))
        map(lambda c: c.extract(), comments)
        
        ##
        ## style selectors
        ##
        
        rules = []
        
        for style in page.find("style") or []:
            css_body = str(style)
            these_rules, these_leftover = self._parse_style_rules(css_body)
            rules.extend(these_rules)
            
            if these_leftover:
                style.text = '\n'.join(['%s {%s}' % (k, v) for (k, v) in these_leftover])
            elif not self.keep_style_tags:
                style.extract()
                       
        if self.external_styles:
            for stylefile in self.external_styles:
                print stylefile
                if stylefile.startswith('http://'):
                    css_body = urllib.urlopen(stylefile).read()
                elif os.path.exists(stylefile):
                    try:
                        f = codecs.open(stylefile)
                        css_body = f.read()
                    finally:
                        f.close()
                else:
                    raise ValueError(u"Could not find external style: %s" % stylefile) 
                these_rules, these_leftover = self._parse_style_rules(css_body)
                rules.extend(these_rules)              
            
        for selector, style in rules:
            class_ = ''
            if ':' in selector:
                selector, class_ = re.split(':', selector, 1)
                class_ = ':%s' % class_

            #sel = CSSSelector(selector)
            items = page.findSelect(selector)
            for item in items:
                old_style = item.get('style','')
                new_style = _merge_styles(old_style, style, class_)
                item['style'] = new_style
                self._style_to_basic_html_attributes(item, new_style)

        for item in page.findAll(lambda tag: tag.get('class', None) != None):
            # delete the 'class' attribute
            del item['class']            

        ##
        ## URLs
        ##
        if self.base_url:
            for attr in ('href', 'src'):
                for item in page.findAll(lambda tag: tag.get(attr, None)!= None):
                    item[attr] = urlparse.urljoin(self.base_url, item[attr])
        
        # The default __repr__ encoding for the used version of BeautifulSoup is utf-8
        return str(page).replace('<head/>','<head></head>')
    
    def _style_to_basic_html_attributes(self, element, style_content):
        """given an element and styles like 
        'background-color:red; font-family:Arial' turn some of that into HTML
        attributes. like 'bgcolor', etc.
        
        Note, the style_content can contain pseudoclasses like:
        '{color:red; border:1px solid green} :visited{border:1px solid green}'
        """
        if style_content.count('}') and \
          style_content.count('{') == style_content.count('{'):
            style_content = style_content.split('}')[0][1:]
            
        attributes = {}
        for key, value in [x.split(':') for x in style_content.split(';')
                           if len(x.split(':'))==2]:
            key = key.strip()
            
            if key == 'text-align':
                attributes['align'] = value.strip()
            elif key == 'background-color':
                attributes['bgcolor'] = value.strip()
            elif key == 'width':
                value = value.strip()
                if value.endswith('px'):
                    value = value[:-2]
                attributes['width'] = value
            #else:
            #    print "key", repr(key)
            #    print 'value', repr(value)
            
        for key, value in attributes.items():
            if key in element:
                # already set, don't dare to overwrite
                continue
            element[key] = value
                    
def transform(html, base_url=None):
    return Premailer(html, base_url=base_url).transform()
        
        
if __name__=='__main__':
    
    html = """<html>
        <head>
        <title>Test</title>
        <style>
        h1, h2 { color:red; }
        strong { 
          text-decoration:none
          }
        p { font-size:2px }
        p.footer { font-size: 1px}
        </style>        
        </head>
        <body>
        <h1>Hi!</h1>
        <p><strong>Yes!</strong></p>
        <p class="footer" style="color:red">Feetnuts</p>
        <img href="/images/logo.png"/>
        <a href="">28 Wins</a>
        </body>
        </html>"""
    print transform(html, base_url="http://www.28wins.com")
    
