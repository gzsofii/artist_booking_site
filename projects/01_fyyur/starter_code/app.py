#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import sys
from sqlalchemy import tuple_, or_
from sqlalchemy.inspection import inspect
from models import db, Artist, Venue, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
#db = SQLAlchemy(app) # defined in models.py
db.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///fyyur' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

migrate = Migrate(app, db)

#converts an instance of a model (eg a venue or an artist) to a python dictionary
def model_to_dict(model):
  dict = {}
  for attr in inspect(model).mapper.column_attrs:
    dict[attr.key] = getattr(model, attr.key)
  return dict

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data=[]
  try:
    locations = Venue.query.distinct(tuple_(Venue.city, Venue.state)).all() # distinc locations
    current_time = datetime.now()
    for loc in locations:
      venues = Venue.query.filter_by(city=loc.city, state=loc.state).with_entities(Venue.name, Venue.id).all()
      venues_dict = []
      for venue in venues:
        #print(type(venue)) # it has type Row
        vdict = venue._asdict()
        shows_count = Show.query.filter(Show.venue_id==venue.id, Show.start_time>current_time).count()
        vdict["num_upcoming_shows"] = shows_count
        venues_dict.append(vdict)
      loc_body = {
        "city": loc.city,
        "state": loc.state,
        "venues": venues_dict
      }
      data.append(loc_body)
  except:
    print(sys.exc_info())
  
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  current_time = datetime.now()
  venues = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()
  
  #print(venues)
  venues_body = []
  for venue in venues:
    shows_count = Show.query.filter(Show.venue_id==venue.id, Show.start_time>current_time).count()
    body = {
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_shows': shows_count
    }
    venues_body.append(body)
  response = {
    "count": len(venues),
    "data": venues_body,
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = Venue.query.get(venue_id)
  #print(type(venue)) # it has type Venue
  data = model_to_dict(venue)
  
  #shows = Show.query.filter_by(venue_id=venue_id).all()
  shows = db.session.query(Show, Venue, Artist).join(Venue, Artist).filter(Venue.id==venue_id).all()
  past_shows = []
  upcoming_shows = []

  current_time = datetime.now()
  for show in shows:
    #artist = Artist.query.get(show.artist_id)
    s = {
      "artist_id": show.Artist.id,
      "artist_name": show.Artist.name,
      "artist_image_link": show.Artist.image_link,
      "start_time": show.Show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    if current_time > show.Show.start_time:
      past_shows.append(s)
    else:
      upcoming_shows.append(s)

  data["past_shows"] =  past_shows
  data["upcoming_shows"] = upcoming_shows
  data["past_shows_count"] = len(past_shows)
  data["upcoming_shows_count"] = len(upcoming_shows)

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    print("request data: ", request.form)
    venue = Venue(
      name = request.form.get('name'),
      city = request.form.get('city'),
      state = request.form.get('state'),
      address = request.form.get('address'),
      phone = request.form.get('phone'),
      genres = request.form.getlist('genres'),
      facebook_link = request.form.get('facebook_link'),
      image_link = request.form.get('image_link'),
      website_link = request.form.get('website_link'),
      seeking_talent = not not request.form.get('seeking_talent'), # convert to boolean
      seeking_description = request.form.get('seeking_description'),
    )    
    db.session.add(venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')

#DELETE venue
@app.route('/venues/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
  try:
    print('Delete venue ', venue_id)
    venue = Venue.query.get(venue_id)
    db.session.delete(venue)
    db.session.commit()
    flash("Venue deleted!")
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash("Couldn't delete venue.")
    return redirect(url_for('venues'))
  finally:
    db.session.close()
  return render_template('pages/home.html')


  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage



#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = Artist.query.with_entities(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  current_time = datetime.now()
  artists = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).all()
  #print(venues)
  artists_body = []
  for artist in artists:
    shows_count = Show.query.filter(Show.artist_id==artist.id, Show.start_time>current_time).count()
    body = {
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_shows': shows_count
    }
    artists_body.append(body)
  response = {
    "count": len(artists),
    "data": artists_body,
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.get(artist_id)
  data = model_to_dict(artist)

  shows = Show.query.filter_by(artist_id=artist_id).all()
  past_shows = []
  upcoming_shows = []

  current_time = datetime.now()
  for show in shows:
    venue = Venue.query.get(show.venue_id)
    s = {
      "venue_id": show.venue_id,
      "venue_name": venue.name,
      "venue_image_link": venue.image_link,
      "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    if current_time > show.start_time:
      past_shows.append(s)
    else:
      upcoming_shows.append(s)

  data["past_shows"] =  past_shows
  data["upcoming_shows"] = upcoming_shows
  data["past_shows_count"] = len(past_shows)
  data["upcoming_shows_count"] = len(upcoming_shows)

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  form = ArtistForm(obj=artist)
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    artist = Artist.query.get(artist_id)
    artist.name = request.form.get('name')
    artist.city = request.form.get('city')
    artist.state = request.form.get('state')
    artist.phone = request.form.get('phone')
    artist.genres = request.form.getlist('genres')
    artist.facebook_link = request.form.get('facebook_link')
    artist.image_link = request.form.get('image_link')
    artist.website_link = request.form.get('website_link')
    artist.seeking_venue = not not request.form.get('seeking_venue')
    artist.seeking_description = request.form.get('seeking_description')
    
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' is successfully updated!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id) # venue.id and name would be enough
  form = VenueForm(obj=venue)
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    
    venue.name = request.form.get('name')
    venue.city = request.form.get('city')
    venue.state = request.form.get('state')
    venue.address = request.form.get('address')
    venue.phone = request.form.get('phone')
    venue.genres = request.form.getlist('genres')
    venue.facebook_link = request.form.get('facebook_link')
    venue.image_link = request.form.get('image_link')
    venue.website_link = request.form.get('website_link')
    venue.seeking_talent = not not request.form.get('seeking_talent')
    venue.seeking_description = request.form.get('seeking_description')

    db.session.commit()
    flash('Venue ' + request.form['name'] + ' is successfully updated!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be modified.')
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    #request.form is of type ImmutableMultiDict
    # print(request.form)
    #artist = Artist(**request.form.to_dict())
    artist = Artist(
      name = request.form.get('name'),
      city = request.form.get('city'),
      state = request.form.get('state'),
      phone = request.form.get('phone'),
      genres = request.form.getlist('genres'),
      facebook_link = request.form.get('facebook_link'),
      image_link = request.form.get('image_link'),
      website_link = request.form.get('website_link'),
      seeking_venue = not not request.form.get('seeking_venue'), # converting to boolean
      seeking_description = request.form.get('seeking_description'),
    )

    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = db.session.query(Show, Artist, Venue).join(Artist, Venue).all()
  data = []
  for show in shows:
    #venue = Venue.query.get(show.venue_id)
    #artist = Artist.query.get(show.artist_id)
    body = {
      "venue_id": show.Venue.id,
      "venue_name": show.Venue.name, 
      "artist_id": show.Artist.id,
      "artist_name": show.Artist.name,
      "artist_image_link": show.Artist.image_link,
      "start_time": show.Show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    data.append(body)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    show = Show(
      artist_id=request.form.get('artist_id'),
      venue_id=request.form.get('venue_id'),
      start_time=request.form.get('start_time')
    )
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')

@app.route('/shows/search', methods=['POST'])
def search_shows():
  location_term = request.form.get('location_search_term', '')
  artist_term = request.form.get('artist_search_term', '')
  venue_term = request.form.get('venue_search_term', '')
  shows = db.session.query(Show, Artist, Venue) \
    .join(Artist, Venue)\
    .filter(\
      or_(Venue.city.ilike('%' + location_term + '%'), Venue.state.ilike('%' + location_term + '%')), \
      Artist.name.ilike('%' + artist_term + '%'),\
      Venue.name.ilike('%' + venue_term + '%'))\
    .all()
  print(shows)
  
  data = []
  for show in shows:
    body = {
      'artist_id': show.Artist.id,
      'artist_name': show.Artist.name,
      'artist_image_link': show.Artist.image_link,
      'venue_id': show.Venue.id,
      'venue_name': show.Venue.name,
      'start_time': show.Show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    data.append(body)
  print(data)
  response = {
    'num_shows': len(data),
    'data': data
  }
  return render_template('pages/search_shows.html', results=response)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
