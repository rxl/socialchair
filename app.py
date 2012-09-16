import os
from flask import Flask, render_template, send_from_directory, url_for, session, request, redirect
import json

#----------------------------------------
# initialization
#----------------------------------------

app = Flask(__name__)

app.config.update(
    DEBUG = True,
)

app.config["SECRET_KEY"] = '\xcba\x95A\x93G\xb5}fG\x1a\xe0w<2\xf55`\x16\xc1\x0f[\xd5}'

#----------------------------------------
# facebook and graphmuse apis
#----------------------------------------

from flaskext.oauth import OAuth

if os.environ.get("PORT"):
	APP_DOMAIN = 'http://socialchair.me'
	FACEBOOK_APP_NAME = 'SocialChair'
	FACEBOOK_APP_ID = '353832784698867'
	FACEBOOK_APP_SECRET = '321ac2425cc45427b9a795a116965026'
else:
	APP_DOMAIN = 'http://localhost:5000'
	FACEBOOK_APP_NAME = 'SocialChair_'
	FACEBOOK_APP_ID = '441691665874832'
	FACEBOOK_APP_SECRET = '828a3383ef382beb87fdacedb32523ae'

oauth = OAuth()
facebook = oauth.remote_app('facebook',
	base_url='https://graph.facebook.com/',
	request_token_url=None,
	access_token_url='/oauth/access_token',
	authorize_url='https://www.facebook.com/dialog/oauth',
	consumer_key=FACEBOOK_APP_ID,
	consumer_secret=FACEBOOK_APP_SECRET,
	request_token_params={'scope': ('email, user_actions.music, friends_actions.music, create_event, user_events')}
)

graphmuse_api_base_url = 'https://api.graphmuse.com:8081/clusters?merging=2&auth='

#----------------------------------------
# authentication and login
#----------------------------------------

def pop_all_login_credentials_from_session():
	session.pop('logged_in', None)
	session.pop('facebook_token', None)
	session.pop('facebook_id', None)
	session.pop('name', None)

@facebook.tokengetter
def get_facebook_token():
	return session.get('facebook_token')

@app.route("/facebook_authorized")
@facebook.authorized_handler
def facebook_authorized(resp):
	next_url = request.args.get('next') or url_for('index')
	if resp is None or 'access_token' not in resp:
		error = 'You could not be signed in.'
		return redirect(next_url)

	session['logged_in'] = True
	session['facebook_token'] = (resp['access_token'], '')

	me = facebook.get('/me')

	if 'id' in me.data and 'name' in me.data and 'username' in me.data:
		facebook_id = me.data['id']
		name = me.data['name']
		username = me.data['username']
	else:
		error = 'You could not be signed in.'
		pop_all_login_credentials_from_session()
		return redirect(next_url)

	session['facebook_id'] = facebook_id
	session['name'] = name
	session['username'] = username

	email = None
	if 'email' in me.data:
		email = me.data['email']
	else:
		error = 'You could not be signed in.'
		pop_all_login_credentials_from_session()
		return redirect(next_url)
	session['email'] = email

	print "Username: %s, Email: %s" % (username, email)

	return redirect("/create_event")

@app.route("/facebook_login")
def facebook_login():
	return facebook.authorize(callback=url_for('facebook_authorized',
		next=request.args.get('next'), _external=True))

@app.route("/logout")
def logout():
	pop_all_login_credentials_from_session()
	return redirect(url_for('index'))

#----------------------------------------
# api
#----------------------------------------

def invite_friends_to_facebook_event(event_id, friends):
	response = facebook.post('/' + event_id + '/invited?users=' + friends)
	return response.data

@app.route('/_invite_friends_to_facebook_event', methods=['POST'])
def _invite_friends_to_facebook_event():
	if 'friends' in request.form and 'event_id' in request.form:
		friends = request.form['friends']
		event_id = request.form['event_id']
	else:
		return json.dumps({ "error": "invalid parameters" }), 400

	data = invite_friends_to_facebook_event(friends, event_id)
	#data = "it didn't actually invite friends on facebook"

	return json.dumps({"data": data})

@app.route('/_push_event_to_facebook', methods=['POST'])
def _push_event_to_facebook():
	if 'name' in request.form and 'description' in request.form and 'location' in request.form and 'start_time' in request.form and 'end_time' in request.form:
		name = request.form['name']
		description = request.form['description']
		location = request.form['location']
		start_time = request.form['start_time']
		end_time = request.form['end_time']
		# '2012-09-16T19:00:00-0700'
	else:
		return json.dumps({ "error": "invalid parameters" }), 400
	
	data = {'name': name, 'start_time': start_time, 'end_time': end_time, 'description': description, 'location': location, 'privacy_type':'SECRET'}
	response = facebook.post('/me/events', data=data)
	if 'id' in response.data:
		event_id = response.data['id']
	else:
		return json.dumps({ "error": "facebook event creation failed", "facebook_response": response.data}), 500

	return json.dumps({ "event_id": event_id })

import requests

def get_clusters_for_access_token(access_token):
	with open('static/ryan.json', 'r') as f:
		json_data = f.read()
		clusters = json.loads(json_data)

	"""graphmuse_get_clusters_url = graphmuse_api_base_url + access_token
	response = requests.get(graphmuse_get_clusters_url, verify=False)
	json_response = response.json
	print json_response

	if 'clusters' in json_response:
		clusters = json_response['clusters']
	else:
		return None"""

	return clusters

"""@app.route("/_get_clusters_from_graphmuse", methods=['POST'])
def _get_clusters_from_graphmuse():
	if 'access_token' in request.form:
		access_token = request.form['access_token']
	else:
		return json.dumps({ "error" : "Missing parameters." }), 400

	clusters = get_clusters_for_access_token(access_token)

	return json.dumps({ "clusters" : clusters })"""

#----------------------------------------
# controllers
#----------------------------------------

@app.route('/favicon.ico')
def favicon():
	return send_from_directory(os.path.join(app.root_path, 'static'), 'ico/favicon.ico')

@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

from collections import defaultdict
import operator

def get_songs_for_users(users):
	song_ids_and_counts = defaultdict(int)

	for user in users:
		listens = facebook.get('/' + user['id'] + "/music.listens?fields=data")
		for listen in listens.data['data']:
			listen_data = listen['data']
			song = listen_data['song']
			#url = song['url']
			#spotifyid = url.split("/").pop()
			facebookid = song['id']
			#title = song['title']
			song_ids_and_counts[str(facebookid)] += 1

	sorted_song_ids_and_counts = sorted(song_ids_and_counts.iteritems(), key=operator.itemgetter(1), reverse=True)

	songs = []

	for song_id_and_count in sorted_song_ids_and_counts:
		song_fbid = song_id_and_count[0]
		response = facebook.get('/' + song_fbid)
		song_data = response.data
		url = song_data['url']
		spotifyid = url.split("/").pop()
		title = song_data['title']
		data = song_data['data']
		musician_object = data['musician']
		if len(musician_object) >= 1:
			artist = musician_object[0]['name']
		songs.append({ "id": spotifyid, "track": title, "artist": artist })

	return songs

def get_playlists_direct():
	playlists = [{'name': 'RnB', 'songs': [{'track': u'Shot For Me', 'id': u'6k7b4mcxLP5HPo6hNoXoM6', 'artist': u'Drake'}, {'track': u'Crew Love', 'id': u'0TiC3GtlMCskf2hIUIBcDV', 'artist': u'Drake'}, {'track': u'Over My Dead Body', 'id': u'749SJvmRHD43wFUnBtUJ36', 'artist': u'Drake'}, {'track': u'Becky - Explicit Album Version', 'id': u'3a63I44dGAmaK5c2uetjIy', 'artist': u'Plies'}, {'track': u'Headlines - Explicit Version', 'id': u'7kfTqGMzIHFWeBeOJALzRf', 'artist': u'Drake'}, {'track': u'Living Better Now', 'id': u'7wfGx8bfYFGA3Ongr3ZGia', 'artist': u'Jamie Foxx'}, {'track': u'Doing It Wrong', 'id': u'06UZYUYbMqpaawLgoKwSw9', 'artist': u'Drake'}, {'track': u'In This Life', 'id': u'3MEEzgFPWUAOV9OSBIBLcK', 'artist': u'Mike Stud'}, {'track': u'She Will', 'id': u'08N3wNB4s9maD4EvaLmSd5', 'artist': u'Lil Wayne'}, {'track': u'Moment 4 Life', 'id': u'0ConttVd0Ebk3dLNquOmh0', 'artist': u'Nicki Minaj'}, {'track': u'Take Care', 'id': u'4wTMBYRE6xVTIUQ6fEudsJ', 'artist': u'Drake'}, {'track': u'Still Got It - Explicit Version', 'id': u'4LedC9uDxADBqr0N2Kw9cF', 'artist': u'Tyga'}, {'track': u'Slow Jamz - Feat. Kanye West & Jamie Foxx   Edited Album Version', 'id': u'4w00phkN8wWRCa5KWP8sTy', 'artist': u'Twista feat. Kayne West & Jamie Foxx'}, {'track': u"Can't Get Enough featuring Trey Songz - Explicit Version", 'id': u'20wR5XQpaL1uvVY8gmc4uY', 'artist': u'J. Cole'}, {'track': u'BTSTU (Edit)', 'id': u'2NRRrr8ylDK38KD3Ffbw4K', 'artist': u'Jai Paul'}]}, {'name': 'DrumNBass', 'songs': [{'track': u'Carny - Jaceo Remix', 'id': u'2y9gDByHTAfq1RvFSnLBrh', 'artist': u'Pleasurekraft'}, {'track': u'Anubis - Mike Vale Remix', 'id': u'2WdE0jBgftULj3mzlI4O5v', 'artist': u'Pleasurekraft'}, {'track': u'Puppy', 'id': u'1Fy7Ies2cwUgF06WU0Ynll', 'artist': u'Netsky'}, {'track': u'Tarantula - Uner Remix', 'id': u'4K1hDtGGoHzqH1novN0cs0', 'artist': u'Pleasurekraft'}, {'track': u'Carny - Chase Buch & Nick Olivetti Remix', 'id': u'1GW27ATL8GqAzQQP5QS3nW', 'artist': u'Pleasurekraft'}, {'track': u'Jetlag Funk', 'id': u'4usbrIvBPME1Va6LrpgHYy', 'artist': u'Netsky'}, {'track': u'See The Sun - Aurosonic Remix', 'id': u'6qTc8X3Q9xxqGIXS8efVUO', 'artist': u'Matt Darey'}, {'track': u'Breastfed - Original', 'id': u'7pCvz68a3qatdVlHo5cgeE', 'artist': u'Pleasurekraft'}, {'track': u'Detonate', 'id': u'04KwA9VVn0nr2bY6G0xcJx', 'artist': u'Netsky'}, {'track': u'Tarantula - Io Remix', 'id': u'7xAW0ZzeLX68tFDmO3PwIm', 'artist': u'Pleasurekraft'}, {'track': u'When Darkness Falls', 'id': u'6Eu3hdlvRRuRgmI0GBSP8s', 'artist': u'Netsky'}, {'track': u'Dubplate Special', 'id': u'1uAszNKOIG8uEwgtLsRa2k', 'artist': u'Netsky'}]}, {'name': 'House', 'songs': [{'track': u'Mozart - Radio Edit', 'id': u'3o6hnYHQGPs59NUQmJ1bqh', 'artist': u'Mat Zo'}, {'track': u'Turbulence - Radio Edit', 'id': u'5uIvDtwNnpOze5L0sI0zJc', 'artist': u'Steve Aoki'}, {'track': u'Synthetic Symphony - Deadmau5 Remix', 'id': u'3ORFanYtGh5kQddyZHVoIx', 'artist': u'Deadmau5'}, {'track': u'Raise Your Weapon - Stimming Remix', 'id': u'4WmK2KhXjfadtmWsJzFkXR', 'artist': u'Deadmau5'}, {'track': u'The Longest Road - Deadmau5 Remix', 'id': u'4ivW56naQHjGggnaybM0tu', 'artist': u'Morgan Page'}, {'track': u'Levels - Original Version', 'id': u'0tDbl1SVkdSI4Efi0sA3A8', 'artist': u'Avicii'}, {'track': u'Save The World (Style Of Eye & Carli Remix)', 'id': u'7eAfGJZZNTb5QARXQlRvjd', 'artist': u'Swedish House Mafia'}, {'track': u'New Lands', 'id': u'2ndeRWn6rZ2y4N5LY3q9wf', 'artist': u'Justice'}, {'track': u'Cinema - Radio Edit', 'id': u'0Rsm0c4rfOweDWqw4UlHUO', 'artist': u'Benny Benassi'}, {'track': u'Move For Me - Extended Mix', 'id': u'6pZAxj9PQm3dgRfy1jTGU6', 'artist': u'Kaskade & Deadmau5'}, {'track': u'Barbra Streisand', 'id': u'7byLULpzbBTguW9wrEjBPt', 'artist': u'Duck Sauce'}, {'track': u'Community Funk - deadmau5 Remix', 'id': u'3PFhljHTZVruNfqcUSk9Ky', 'artist': u'Burufunk'}, {'track': u'Not Exactly', 'id': u'5pH46XcKf23LS0oZSzYTrD', 'artist': u'Deadmau 5'}, {'track': u'Strobe - Michael Woods Remix', 'id': u'75wQweic0BlmTzwwSOLNkb', 'artist': u'Deadmau5'}, {'track': u"Arguru (EDX's 5un5hine Remix)", 'id': u'0pQfS4hhGau00QdXQSUQol', 'artist': u'Deadmau5'}, {'track': u'HR 8938 Cephei - Original Mix', 'id': u'7jXQTIKMztby1IyN1FRNnR', 'artist': u'Deadmau5'}, {'track': u'Scary Monsters And Nice Sprites', 'id': u'4rwpZEcnalkuhPyGkEdhu0', 'artist': u'Skrillex'}, {'track': u'Set Adrift On Memory Bliss - Radio Edit', 'id': u'4TK1YzdHTJp3RKxJpllBa9', 'artist': u'P.M. Dawn'}]}, {'name': 'Popular', 'songs': [{'track': u'Gangnam Style','id': u'03UrZgTINDqvnUMbbIMhql','artist': u'Psy'}, {'track': u'Glad You Came', 'id': u'1OXfWI3FQMdsKKC6lkvzSx', 'artist': u'The Wanted'}, {'track': u'Party Rock Anthem', 'id': u'70dWrqAp30TmWeibQkn0i7', 'artist': u'LMFAO'}, {'track': u'Se\xf1orita', 'id': u'0aj2QKJvz6CePykmlTApiD', 'artist': u'Justin Timberlake'}, {'track': u'Reminds Me Of You', 'id': u'402RUhrIiFxtJ2rSovAXuI', 'artist': u'LMFAO'}, {'track': u'Lights & Music - Boys Noize Remix', 'id': u'1R6lhY5PqoxQJU5hsMDvjg', 'artist': u'Cut Copy'}]}]
	return playlists

"""def get_songs_direct():
	songs = [{'name': 'RnB', 'songs': [{'track': u'Shot For Me', 'id': u'6k7b4mcxLP5HPo6hNoXoM6', 'artist': u'Drake'}, {'track': u'Crew Love', 'id': u'0TiC3GtlMCskf2hIUIBcDV', 'artist': u'Drake'}, {'track': u'Over My Dead Body', 'id': u'749SJvmRHD43wFUnBtUJ36', 'artist': u'Drake'}, {'track': u'Becky - Explicit Album Version', 'id': u'3a63I44dGAmaK5c2uetjIy', 'artist': u'Plies'}, {'track': u'Headlines - Explicit Version', 'id': u'7kfTqGMzIHFWeBeOJALzRf', 'artist': u'Drake'}, {'track': u'Living Better Now', 'id': u'7wfGx8bfYFGA3Ongr3ZGia', 'artist': u'Jamie Foxx'}, {'track': u'Doing It Wrong', 'id': u'06UZYUYbMqpaawLgoKwSw9', 'artist': u'Drake'}, {'track': u'In This Life', 'id': u'3MEEzgFPWUAOV9OSBIBLcK', 'artist': u'Mike Stud'}, {'track': u'She Will', 'id': u'08N3wNB4s9maD4EvaLmSd5', 'artist': u'Lil Wayne'}, {'track': u'Moment 4 Life', 'id': u'0ConttVd0Ebk3dLNquOmh0', 'artist': u'Nicki Minaj'}, {'track': u'Take Care', 'id': u'4wTMBYRE6xVTIUQ6fEudsJ', 'artist': u'Drake'}, {'track': u'Still Got It - Explicit Version', 'id': u'4LedC9uDxADBqr0N2Kw9cF', 'artist': u'Tyga'}, {'track': u'Slow Jamz - Feat. Kanye West & Jamie Foxx   Edited Album Version', 'id': u'4w00phkN8wWRCa5KWP8sTy', 'artist': u'Twista feat. Kayne West & Jamie Foxx'}, {'track': u"Can't Get Enough featuring Trey Songz - Explicit Version", 'id': u'20wR5XQpaL1uvVY8gmc4uY', 'artist': u'J. Cole'}, {'track': u'BTSTU (Edit)', 'id': u'2NRRrr8ylDK38KD3Ffbw4K', 'artist': u'Jai Paul'}]}, {'name': 'DrumNBass', 'songs': [{'track': u'Carny - Jaceo Remix', 'id': u'2y9gDByHTAfq1RvFSnLBrh', 'artist': u'Pleasurekraft'}, {'track': u'Anubis - Mike Vale Remix', 'id': u'2WdE0jBgftULj3mzlI4O5v', 'artist': u'Pleasurekraft'}, {'track': u'Puppy', 'id': u'1Fy7Ies2cwUgF06WU0Ynll', 'artist': u'Netsky'}, {'track': u'Tarantula - Uner Remix', 'id': u'4K1hDtGGoHzqH1novN0cs0', 'artist': u'Pleasurekraft'}, {'track': u'Carny - Chase Buch & Nick Olivetti Remix', 'id': u'1GW27ATL8GqAzQQP5QS3nW', 'artist': u'Pleasurekraft'}, {'track': u'Jetlag Funk', 'id': u'4usbrIvBPME1Va6LrpgHYy', 'artist': u'Netsky'}, {'track': u'See The Sun - Aurosonic Remix', 'id': u'6qTc8X3Q9xxqGIXS8efVUO', 'artist': u'Matt Darey'}, {'track': u'Breastfed - Original', 'id': u'7pCvz68a3qatdVlHo5cgeE', 'artist': u'Pleasurekraft'}, {'track': u'Detonate', 'id': u'04KwA9VVn0nr2bY6G0xcJx', 'artist': u'Netsky'}, {'track': u'Tarantula - Io Remix', 'id': u'7xAW0ZzeLX68tFDmO3PwIm', 'artist': u'Pleasurekraft'}, {'track': u'When Darkness Falls', 'id': u'6Eu3hdlvRRuRgmI0GBSP8s', 'artist': u'Netsky'}, {'track': u'Dubplate Special', 'id': u'1uAszNKOIG8uEwgtLsRa2k', 'artist': u'Netsky'}]}, {'name': 'House', 'songs': [{'track': u'Mozart - Radio Edit', 'id': u'3o6hnYHQGPs59NUQmJ1bqh', 'artist': u'Mat Zo'}, {'track': u'Turbulence - Radio Edit', 'id': u'5uIvDtwNnpOze5L0sI0zJc', 'artist': u'Steve Aoki'}, {'track': u'Synthetic Symphony - Deadmau5 Remix', 'id': u'3ORFanYtGh5kQddyZHVoIx', 'artist': u'Deadmau5'}, {'track': u'Raise Your Weapon - Stimming Remix', 'id': u'4WmK2KhXjfadtmWsJzFkXR', 'artist': u'Deadmau5'}, {'track': u'The Longest Road - Deadmau5 Remix', 'id': u'4ivW56naQHjGggnaybM0tu', 'artist': u'Morgan Page'}, {'track': u'Levels - Original Version', 'id': u'0tDbl1SVkdSI4Efi0sA3A8', 'artist': u'Avicii'}, {'track': u'Save The World (Style Of Eye & Carli Remix)', 'id': u'7eAfGJZZNTb5QARXQlRvjd', 'artist': u'Swedish House Mafia'}, {'track': u'New Lands', 'id': u'2ndeRWn6rZ2y4N5LY3q9wf', 'artist': u'Justice'}, {'track': u'Cinema - Radio Edit', 'id': u'0Rsm0c4rfOweDWqw4UlHUO', 'artist': u'Benny Benassi'}, {'track': u'Move For Me - Extended Mix', 'id': u'6pZAxj9PQm3dgRfy1jTGU6', 'artist': u'Kaskade & Deadmau5'}, {'track': u'Barbra Streisand', 'id': u'7byLULpzbBTguW9wrEjBPt', 'artist': u'Duck Sauce'}, {'track': u'Community Funk - deadmau5 Remix', 'id': u'3PFhljHTZVruNfqcUSk9Ky', 'artist': u'Burufunk'}, {'track': u'Not Exactly', 'id': u'5pH46XcKf23LS0oZSzYTrD', 'artist': u'Deadmau 5'}, {'track': u'Strobe - Michael Woods Remix', 'id': u'75wQweic0BlmTzwwSOLNkb', 'artist': u'Deadmau5'}, {'track': u"Arguru (EDX's 5un5hine Remix)", 'id': u'0pQfS4hhGau00QdXQSUQol', 'artist': u'Deadmau5'}, {'track': u'HR 8938 Cephei - Original Mix', 'id': u'7jXQTIKMztby1IyN1FRNnR', 'artist': u'Deadmau5'}, {'track': u'Scary Monsters And Nice Sprites', 'id': u'4rwpZEcnalkuhPyGkEdhu0', 'artist': u'Skrillex'}, {'track': u'Set Adrift On Memory Bliss - Radio Edit', 'id': u'4TK1YzdHTJp3RKxJpllBa9', 'artist': u'P.M. Dawn'}]}, {'name': 'Popular', 'songs': [{'track': u'Glad You Came', 'id': u'1OXfWI3FQMdsKKC6lkvzSx', 'artist': u'The Wanted'}, {'track': u'Party Rock Anthem', 'id': u'70dWrqAp30TmWeibQkn0i7', 'artist': u'LMFAO'}, {'track': u'Se\xf1orita', 'id': u'0aj2QKJvz6CePykmlTApiD', 'artist': u'Justin Timberlake'}, {'track': u'Reminds Me Of You', 'id': u'402RUhrIiFxtJ2rSovAXuI', 'artist': u'LMFAO'}, {'track': u'Lights & Music - Boys Noize Remix', 'id': u'1R6lhY5PqoxQJU5hsMDvjg', 'artist': u'Cut Copy'}]}]
	return songs"""

@app.route("/get_songs_direct_api", methods=['GET'])
def get_songs_direct_api():
	return json.dumps(get_songs_direct())

def chunks(list, size_of_chunk):
	for i in xrange(0, len(list), size_of_chunk):
		yield list[i:i+size_of_chunk]

@app.route("/party", methods=['POST'])
def party():
	if 'friends' in request.form and 'eventName' in request.form and 'eventId' in request.form:
		friends = json.loads(request.form['friends'])
		event_name = request.form['eventName']
		event_id = request.form['eventId']
	else:
		return json.dumps({ "error" : "Missing parameters." }), 400

	friend_ids = []
	for friend in friends:
		friend_ids.append(friend['id'])
	friend_string = ",".join(friend_ids)

	#data = invite_friends_to_facebook_event(event_id, friend_string)
	#print data

	#songs = get_songs_for_users(friends)
	playlists_raw = get_playlists_direct()

	playlists_formatted = []
	for playlist in playlists_raw:
		songids = []
		songs = playlist['songs']
		for song in songs:
			songids.append(song['id'])
		song_string = ",".join(songids)
		playlists_formatted.append({"name": playlist['name'], "songs": song_string })

	print playlists_formatted
	#songids = []


	#default_playlist = {"name": "Top Songs" }
	#spotifyid_shortlist = []
	#for song in songs[:15]:
	#	spotifyid_shortlist.append(song['id'])
	#default_playlist['songs'] = ",".join(spotifyid_shortlist)

	"""for chunk in chunks(songids, 15):
		song_string = ",".join(chunk)
		playlists.append({"name": names[i], "songs": song_string })
		i += 1"""

	for friend in friends:
		friend['i'] = friend['id']

	#print songs
	#songs_formatted = json.dumps(songs).replace("'", r"\'").replace('"', r"\"")
	#print songs_formatted
	#attendees = [{'i': '1341720286', 'name': 'Dan Shipper'}, {'i': '640921673', 'name': 'Chuck Moyes'}, {'i': '528415896', 'name': 'Tony Diepenbrock IV'}, {'i': '502727430', 'name': 'Patrick Leahy'}, {'i': '567412775', 'name': 'Justin Meltzer'}, {'i': '100002498063553', 'name': 'Mitchell Stern'}]
	#party_name = "PennApps After-Party"
	#playlist_name1 = "Electronic"
	#playlist_name2 = "Drum and Bass"
	#songs1 = "49MsPNQCOmxvIYi9AdoPzY,6fUlrsHaz4QfCNF31rk2dU,5KiTsR2h8jnzkvTeucxoAn,6kidUwWb8tB9ktfy7U76iX,6mlUEdb90RqwUisnp65lG7,6KOEK6SeCEZOQkLj5M1PxH,3psrcZoGRaWh6FMGael1NX,3EHLii6bnZxJxsCfLlIb83,0xJtHBdhpdLuClaSQYddI4,6fsdOFwa9lTG7WKL9sEWRU"
	#songs2 = "49MsPNQCOmxvIYi9AdoPzY,6fUlrsHaz4QfCNF31rk2dU,5KiTsR2h8jnzkvTeucxoAn,6kidUwWb8tB9ktfy7U76iX,6mlUEdb90RqwUisnp65lG7,6KOEK6SeCEZOQkLj5M1PxH,3psrcZoGRaWh6FMGael1NX,3EHLii6bnZxJxsCfLlIb83,0xJtHBdhpdLuClaSQYddI4,6fsdOFwa9lTG7WKL9sEWRU"
	#playlists = [{ "name": playlist_name1, "songs": songs1 }, { "name": playlist_name2, "songs": songs2 }]

	return render_template('party_page.html', name=event_name, attendees=friends, playlists=playlists_formatted)

@app.route("/invite_friends/<event_id>/<event_name>")
def invite_friends(event_id, event_name):
	if 'facebook_token' in session and len(session) > 0:
		access_token = session['facebook_token'][0]
		clusters = get_clusters_for_access_token(access_token)
		print clusters

	return render_template('invite_friends.html', clusters=clusters, event_id=event_id, event_name=event_name)

@app.route("/create_event")
def create_event():
	return render_template('create_event.html')

@app.route("/")
def index():
	if 'logged_in' in session:
		return render_template('index.html')
	else:
		return render_template('landing.html')

#----------------------------------------
# launch
#----------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)