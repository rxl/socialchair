import os
from flask import Flask, render_template, send_from_directory, url_for, session, request, redirect

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
	request_token_params={'scope': ('email, user_actions.music, friends_actions.music, create_event')}
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

	return redirect(next_url)

@app.route("/facebook_login")
def facebook_login():
	return facebook.authorize(callback=url_for('facebook_authorized',
		next=request.args.get('next'), _external=True))

@app.route("/logout")
def logout():
	pop_all_login_credentials_from_session()
	return redirect(url_for('index'))

#----------------------------------------
# controllers
#----------------------------------------

import json

@app.route('/create_event', methods=['POST'])
def create_event():
	if 'name' in request.form and 'description' in request.form and 'location' in request.form and 'start_time' in request.form and 'end_time' in request.form:
		name = request.form['name']
		description = request.form['description']
		location = request.form['location']
		start_time = request.form['start_time']
		end_time = request.form['end_time']
		# '2012-09-16T19:00:00-0700'
		users = request.form['users']
	else:
		return json.dumps({ "error": "invalid parameters" }), 400
	
	data = {'name': name, 'start_time': start_time, 'end_time': end_time, 'description': description, 'location': location, 'privacy_type':'SECRET'}
	response = facebook.post('/me/events', data=data)
	event_id = response.data['id']

	response = facebook.post('/' + event_id + '/invited?users=' + users)
	print "added users: %s" % str(response.data)

	return json.dumps({"event_id": event_id})

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'ico/favicon.ico')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route("/")
def index():
    return render_template('index.html')

#----------------------------------------
# launch
#----------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)