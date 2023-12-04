""" Copyright (c) 2023 x93

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Optional, Dict, Any, Tuple
from user_agent import generate_user_agent
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from ebooklib import epub
import logging
import json


class WattyAPI:
  def __init__(
    self, static_user_agent: Optional[str] = None,
    rolling_user_agent: bool = True
  ) -> None:
    self.static_user_agent: Optional[str] = static_user_agent
    self.rolling_user_agent: bool = rolling_user_agent

  def _generate(self):
    if self.rolling_user_agent:
      self._ua = generate_user_agent()
    else:
      self._ua = self.static_user_agent

  async def _get(self, url: str) -> str:
    self._generate()
    data: str = ""
    async with ClientSession() as sess:
      sess.headers['User-Agent'] = self._ua
      async with sess.get(url) as resp:
        if resp.status != 200:
          raise ValueError(
            'Status code of GET request to "{}" is not 200!'.format(url))
        data = await resp.read()
        logging.debug('[200] {}'.format(url))
    return data

  async def get(self, url: str) -> str:
    return (await self._get(url)).decode()

  async def fetchData(self, url: str) -> Dict[str, Any]:
    soup: BeautifulSoup = BeautifulSoup(
      await self.get(url), 'html.parser')

    data: Optional[str] = None
    for x in soup.find_all('script'):
      if x.text.strip().startswith('window.prefetched'):
        data = x.text.strip()

    if not data:
      raise ValueError('"window.prefetched" script not found!')

    return [*json.loads(data.split(' = ', 1)[1][:-1]).values()][0]['data']


class WattyEPUB:
  defaults: Dict[str, Any] = {
    'custom_watty': None,
    'entry_page_title': 'Intro',
    'entry_page_ffile': 'format/intro_format.html',
    'chapter_page_ffile': 'format/chapter_format.html'
  }

  def __init__(self, **settings):
    sts: Dict[str, Any] = \
      self.defaults.copy()
    sts.update(settings)

    for key, st in sts.items():
      setattr(self, key, st)

  def _build_stars(self, rating: float):
    temp: str = '★' * int(rating)
    em: int = 5 - int(rating)
    if rating - int(rating) > 0.5:
      em -= 1
      temp += '⯪'
    temp += '☆'
    return temp

  async def build(self, url: str, file: Optional[str] = None) -> epub.EpubBook:
    book: epub.EpubBook = epub.EpubBook()
    if not self.custom_watty:
      self.watty = WattyAPI()
    else:
      self.watty = self.custom_watty

    metadata: Dict[str, Any] = \
      await self.watty.fetchData(url)

    stars: str = \
      self._build_stars(metadata['group']['rating'])
    apitext: str = \
      metadata['text_url']['text'].split('&')[0] + '&id={}&page='

    book.set_identifier(str(metadata['id']))
    book.set_title(metadata['group']['title'])
    book.add_author(metadata['group']['user']['name'])
    book.add_metadata('DC', 'description', metadata['group']['description'])

    _format: Dict[str, Any] = dict(
      book_title=metadata['group']['title'],
      author=metadata['group']['user']['name'],
      author_user=metadata['group']['user']['username'],
      description=metadata['group']['description'],
      last_modification=metadata['group']['modifyDate']
    )

    caps: List[epub.EpubHtml] = []
    c1 = epub.EpubHtml(title=self.entry_page_title, file_name="intro.xhtml")
    with open(self.entry_page_ffile, 'r', encoding='utf-8') as epff:
      c1.content = epff.read().format(**_format)
    caps.append(c1)

    with open(self.chapter_page_ffile, 'r', encoding='utf-8') as cpff:
      chapterFormat = cpff.read()

    book.set_cover('static/cover.jpg', await self.watty._get(metadata['group']['cover']))
    parts: List[Tuple[str, int]] = \
      [(x['title'], x['id']) for x in metadata['group']['parts']]

    number: int = 1
    for title, _id in parts:
      text: str = await self.watty.get(apitext.format(str(_id)))
      parser: BeautifulSoup = BeautifulSoup(text, 'html.parser')

      for img in parser.find_all('img'):
        imgID: str = \
          img['src'].split('https://')[1].split('/')[1].replace('/', '_')

        imgData: bytes = await self.watty._get(img['src'])
        book.add_item(epub.EpubImage(
            uid=imgID,
            file_name="static/" + imgID + '.jpg',
            media_type="image/jpg",
            content=imgData
        ))

        img['src'] = 'static/' + imgID + '.jpg'

      caps.append(
        epub.EpubHtml(title=title, file_name='{}.xhtml'.format(title)))
      caps[-1].content = chapterFormat.format(
        title=title,
        text=str(parser),
        number=number,
        **_format
      )

      number += 1

    for cap in caps:
      book.add_item(cap)

    book.toc = caps
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = caps

    if not file:
      epub.write_epub(metadata['group']['title'] + '.epub', book, {})

    else:
      epub.write_epub(file, book, {})
