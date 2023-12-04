# Watty
Watty is a, like his name says, book downloader for that popular book page.

## How to use it?
This library is quite easy to use, if you just want to use the API of this site then WattyAPI is for you, and if you want to download those books in EPUB format (the only format supported for now) then WattyEPUB is for you
Also, you need to get the Watt link of the first chapter of the book for all of this to work.

### WattyEPUB
```python
from watty import WattyEPUB

builder = WattyEPUB()
builder.build(
  'https://link.to/the/watt/book', 'output_file.epub')
```

### WattyAPI
```python
from watty import WattyAPI

api = WattyAPI()
# Fetch all the data that Watt provides
print(
  api.fetchData('https://libk.to/the/watt/book'))
```

## TODO
- [ ] Upload package to PyPi  
- [ ] Add support for more output formats  
- [ ] Add a friendly downloader 'click' CLI  
- [ ] Improve logging, and add status hooks  
- [ ] Improve the Chapter and Intro page format  
- [ ] Add support for using the book page, and not the first page of it  

# This project is licensed under the terms of the MIT license.
