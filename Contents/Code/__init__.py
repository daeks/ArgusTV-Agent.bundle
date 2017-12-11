import hashlib, os, re

RE_IMDB_ID = Regex('^tt\d{7}$')
TMDB_BASE_URL = 'http://127.0.0.1:32400/services/tmdb?uri=%s'
TMDB_MOVIE_SEARCH = '/search/movie?query=%s&language=%s'
FREEBASE_URL = 'https://meta.plex.tv/m/%s?lang=%s&ratings=1&reviews=0&extras=1'

IVA_ASSET_URL = 'iva://api.internetvideoarchive.com/2.0/DataService/VideoAssets(%s)?lang=%s&bitrates=%s&duration=%s&adaptive=%d&dts=%d'
IVA_LANGUAGES = {-1   : Locale.Language.Unknown,
                  0   : Locale.Language.English,
                  10  : Locale.Language.German}
                  
COUNTRY_CODE = {'en': 'US',
                'de': 'US'}

def Start():
  
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0'
  
def ValidatePrefs():
  pass

class ArgusTVAgent(Agent.Movies):

  name = 'Argus TV'
  languages = [Locale.Language.NoLanguage, Locale.Language.English, Locale.Language.German]
  primary_provider = True
  contributes_to = ['com.plexapp.agents.none']
  accepts_from = ['com.plexapp.agents.none']

  def search(self, results, media, lang, manual=False):
  
    part = media.items[0].parts[0]
    path = os.path.dirname(part.file)
    (root_file, ext) = os.path.splitext(os.path.basename(part.file))
  
    if os.path.isfile(os.path.join(path, root_file + '.arg')):
      data = Core.storage.load(os.path.join(path, root_file + '.arg'))
      xml_data = XML.ElementFromString(data).xpath('//Recording')[0]
  
      if not media.name:
        url = TMDB_MOVIE_SEARCH % (String.Quote(xml_data.xpath('Title')[0].text, True), Prefs['language'])
      else:
        url = TMDB_MOVIE_SEARCH % (String.Quote(media.name, True), Prefs['language'])
      
      try:
        tmdb_dict = JSON.ObjectFromURL(TMDB_BASE_URL % String.Quote(url, True), sleep=2.0, headers={'Accept': 'application/json'}, cacheTime=CACHE_1DAY)
        if isinstance(tmdb_dict, dict) and 'results' in tmdb_dict:
          for i, movie in enumerate(sorted(tmdb_dict['results'], key=lambda k: k['popularity'], reverse=True)):
            if 'imdb_id' in movie and RE_IMDB_ID.search(movie['imdb_id']):
              id = str(movie['imdb_id'])
            else:
              id = imdb_id_from_tmdb(str(movie['id']))
        
            result = MetadataSearchResult(id=id, name=movie['title'], year=int(movie['release_date'].split('-')[0]) if movie['release_date'] else None, score=100, lang=Prefs['language'])
            results.Append(result)
      except:
       Log('Could not retrieve data from PLEX for: %s' % media.name)
       results.Append(MetadataSearchResult(id = media.id, name = media.name, year = None, score = 100, lang = Prefs['language']))
    else:
      results.Append(MetadataSearchResult(id = media.id, name = media.name, year = None, score = 100, lang = Prefs['language']))

  def update(self, metadata, media, lang):

    part = media.items[0].parts[0]
    path = os.path.dirname(part.file)
    (root_file, ext) = os.path.splitext(os.path.basename(part.file))
    
    if os.path.isfile(os.path.join(path, root_file + '.thmb')):
      data = Core.storage.load(os.path.join(path, root_file + '.thmb'))
      media_hash = hashlib.md5(data).hexdigest()
      if media_hash not in metadata.art:
        metadata.art[media_hash] = Proxy.Media(data, sort_order=1)
        Log('[DNET] Thumbnail added for %s' % metadata.id)
    
    if os.path.isfile(os.path.join(path, root_file + '.arg')):
      data = Core.storage.load(os.path.join(path, root_file + '.arg'))
      xml_data = XML.ElementFromString(data).xpath('//Recording')[0]
      
      metadata.title = xml_data.xpath('Title')[0].text
      metadata.original_title = xml_data.xpath('Title')[0].text
      if xml_data.xpath('SubTitle')[0].text:
        metadata.title = metadata.title + ' - ' + xml_data.xpath('SubTitle')[0].text

      date = Datetime.ParseDate(xml_data.xpath('ProgramStartTime')[0].text)
      metadata.originally_available_at = date.date()
      metadata.year = date.year
      
      metadata.summary = '(' + xml_data.xpath('ChannelDisplayName')[0].text.upper() + ' / ' + date.date().strftime('%d-%b-%Y') + ' ' + date.time().strftime('%H:%M') + ') ' + xml_data.xpath('Description')[0].text
      metadata.studio = xml_data.xpath('ChannelDisplayName')[0].text.upper()
      
      metadata.genres.clear()
      if xml_data.xpath('Category')[0].text:
        for genre in xml_data.xpath('Category')[0].text.split(','):
          metadata.genres.add(genre.strip())
      
      metadata.roles.clear()
      if xml_data.xpath('Actors')[0].text:
        for actor_data in xml_data.xpath('Actors')[0].text.split(';'):
          actor = actor_data.split('(');
          role = metadata.roles.new()
          role.name = actor[0].strip()
          role.role = actor[1][:-1]
      
      try:
        if metadata.id.isdigit():
          Log('[DNET] Lookup Poster for IMDB ID: %s' % metadata.id)
          xmldata = XML.ElementFromURL(url = FREEBASE_URL % (metadata.id, Prefs['language']), cacheTime=CACHE_1DAY)
          
          # Year
          for release_date in xmldata.xpath('originally_available_at'):
            curr_country = release_date.get('country')
            curr_oaa = release_date.get('originally_available_at')
            if curr_country == COUNTRY_CODE.get(Prefs['language']):
              elements = curr_oaa.split('-')
              if len(elements) >= 1 and len(elements[0]) == 4:
                metadata.year = int(elements[0])
          
          # Rating
          for imdb_rating in xmldata.xpath('imdb_ratings'):
            try:
              metadata.rating = (int(imdb_rating.get('audience_score')) or 0) / 10.0
            except TypeError:
              metadata.rating = 0.0

            metadata.audience_rating = 0.0
            metadata.rating_image = 'imdb://image.rating'
            metadata.audience_rating_image = None
            
          # Genres.
          if len(xmldata.xpath('genre')) > 0:
            metadata.genres.clear()
            for genre in [g.get('genre') for g in xmldata.xpath('genre')]:
              metadata.genres.add(genre)
          
          # Actors.
          actors_xml = xmldata.xpath('actor')
          if len(actors_xml) > 0:
            metadata.roles.clear()
            for movie_role in actors_xml:
              role = metadata.roles.new()
              if movie_role.get('role'):
                role.role = movie_role.get('role')
              role.name = movie_role.get('name')

          # Directors.
          director_xml = xmldata.xpath('director')
          if (len(metadata.directors) < 1) and len(director_xml) > 0:
            metadata.directors.clear()
            for movie_director in director_xml:
              director = metadata.directors.new()
              director.name = movie_director.get('name')
            
          # Writers.
          writer_xml = xmldata.xpath('writer')
          if (len(metadata.writers) < 1) and len(writer_xml) > 0:
            metadata.writers.clear()
            for movie_writer in writer_xml:
              writer = metadata.writers.new()
              writer.name = movie_writer.get('name')
          
          # Poster
          for poster in xmldata.xpath('poster'):
            poster_url = poster.get('url')
            try: metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(poster_url).content, sort_order=1)
            except: pass
          
          # Extras
          extras = []
          trailer = False
          for extra in xmldata.xpath('//extra'):
            extra_type = 'primary_trailer' if extra.get('primary') == 'true' else extra.get('type')
            lang_code = int(extra.get('lang_code')) if extra.get('lang_code') else -1
            spoken_lang = IVA_LANGUAGES.get(lang_code) or Locale.Language.Unknown
            bitrates = extra.get('bitrates') or ''
            duration = int(extra.get('duration') or 0)
            adaptive = 1 if extra.get('adaptive') == 'true' else 0
            dts = 1 if extra.get('dts') == 'true' else 0
            
            if not trailer:
              if (extra_type == 'primary_trailer' or extra_type == 'trailer') and spoken_lang == Prefs['language']:
                metadata.extras.add(TrailerObject(url=IVA_ASSET_URL % (extra.get('iva_id'), spoken_lang, bitrates, duration, adaptive, dts), title=metadata.title, thumb=extra.get('thumb') or ''))
                trailer = True
        else:
          Log('[DNET] No IMDB ID: %s' % metadata.id)
      except:
       Log('[DNET] Could not retrieve data from PLEX for: %s' % metadata.title)
                
      Log('[DNET] Metadata loaded for %s' % xml_data.xpath('Title')[0].text)

def imdb_id_from_tmdb(tmdb_id):

  imdb_id = None

  try:
    imdb_id = Core.messaging.call_external_function('com.plexapp.agents.themoviedb', 'MessageKit:GetImdbId', kwargs=dict(tmdb_id=tmdb_id))
  except Ex.HTTPError, e:
    Log('[DNET] Error: Cannot get imdb id from tmdb id (%s) - %s' % (tmdb_id, str(e)))

  if imdb_id is not None:
    imdb_id = imdb_id.replace('tt','')
  else:
    imdb_id = ''

  return imdb_id