import hashlib, os

def Start():

	pass

class ArgusTVAgent(Agent.Movies):

	name = 'Argus TV'
	languages = [Locale.Language.NoLanguage]
	primary_provider = False
	contributes_to = ['com.plexapp.agents.none']

	def search(self, results, media, lang):

		results.Append(MetadataSearchResult(
				id = media.id,
				name = media.name,
				year = None,
				score = 99,
				lang = lang
			)
		)

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
			
			metadata.summary = '(' + xml_data.xpath('ChannelDisplayName')[0].text + ') ' + xml_data.xpath('Description')[0].text
			
			metadata.genres.clear()
			for genre in xml_data.xpath('Category')[0].text.split(','):
				metadata.genres.add(genre.strip())
				
			metadata.roles.clear()
			for actor_data in xml_data.xpath('Actors')[0].text.split(';'):
				actor = actor_data.split('(');
				role = metadata.roles.new()
				role.name = actor[0].strip()
				role.role = actor[1][:-1]
			
			date = Datetime.ParseDate(xml_data.xpath('ProgramStartTime')[0].text)
			metadata.originally_available_at = date.date()
			metadata.year = date.year
			
			Log('Metadata loaded for %s' % xml_data.xpath('Title')[0].text)
