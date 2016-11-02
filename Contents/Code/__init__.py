import hashlib, os

def Start():
  pass
  
def ValidatePrefs():
  pass

class ArgusTVAgent(Agent.Movies):

  name = 'Argus TV'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.none']

  def search(self, results, media, lang):

    results.Append(MetadataSearchResult(id = media.primary_metadata.id, name = media.name, year = None, score = 100, lang = lang))

  def update(self, metadata, media, lang):

    part = media.items[0].parts[0]
    path = os.path.dirname(part.file)
    (root_file, ext) = os.path.splitext(os.path.basename(part.file))
    
    if os.path.isfile(os.path.join(path, root_file + '.thmb')):
      data = Core.storage.load(os.path.join(path, root_file + '.thmb'))
      media_hash = hashlib.md5(data).hexdigest()
      if media_hash not in metadata.art:
        metadata.art[media_hash] = Proxy.Media(data, sort_order=1)
        Log('Thumbnail added for %s' % metadata.id)
    
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
                
      Log('Metadata loaded for %s' % xml_data.xpath('Title')[0].text)
