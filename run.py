import random
import time

import populartimes

from diskcache import Cache
cache = Cache("_cache/")

import googlemaps
GOOGLE_MAPS_API_KEY = "..."
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

from flask import Flask, escape, request, render_template
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route('/')
@app.route('/supermarkets')
def supermarkets():
    livemode = request.args.get("livemode", False)
    queried_location = request.args.get("location", None)

    if livemode or not queried_location:
        location = queried_location
    else:
        location = "97084 Würzburg"

    place_details = get_place_details_for_location(location, livemode=livemode)

    current_time = time.strftime("%Y-%m-%d %H:%M Uhr")

    return render_template("supermarkets.html.jinja2", place_details=place_details, location=queried_location, livemode=livemode, current_time=current_time)


def get_place_details_for_location(location, livemode=False):
    if not location:
        return []

    coordinates = location_to_coordinates(location)

    if not coordinates:
        return []

    search_data = {
        "location": coordinates,
        "radius": 3000,
        # "open_now": True,
        "type": "grocery_or_supermarket",
    }
    places = get_nearby_places(search_data)["results"][:15]
    place_details = [get_place_details(place, search_data) for place in places]

    random.seed(13)

    for place, details in zip(places, place_details):
        details["place"] = place
        details["open_now"] = details["place"].get("opening_hours", {}).get("open_now", True)

        if not livemode:
            details["open_now"] = 1#random.randint(0,1)

            if details["open_now"]:
                details["current_popularity"] = random.randint(10, 100)

        current_popularity = details.get("current_popularity", None)

        if not details["open_now"]:
            details["current_popularity_css_class"] = "popularity-light-unknown"
            details["current_popularity_text"] = "Der Laden hat aktuell geschlossen"
        elif current_popularity == None:
            details["current_popularity_css_class"] = "popularity-light-unknown"
            details["current_popularity_text"] = "Unbekannte Auslastung"
        elif current_popularity < 35:
            details["current_popularity_css_class"] = "popularity-light-good"
            details["current_popularity_text"] = "geringe Besucherzahl"
        elif current_popularity < 70:
            details["current_popularity_css_class"] = "popularity-light-bad"
            details["current_popularity_text"] = "moderate Besucherzahl"
        else:
            details["current_popularity_css_class"] = "popularity-light-worse"
            details["current_popularity_text"] = "hohe Besucherzahl"

    place_details = sorted(place_details, key=lambda p: "%s_%06d" % (
    p["distance"]["rows"][0]["elements"][0]["distance"]["text"], p.get("current_popularity", 999999)))
    return place_details


@cache.memoize(expire=60*60*24)
def location_to_coordinates(location):
    geocode_results = gmaps.geocode(location, region="de")
    if geocode_results:
        return geocode_results[0]["geometry"]["location"]
    else:
        return None

@cache.memoize(expire=60*60*24, tag='places')
def get_nearby_places(search_data):
    return gmaps.places_nearby(**search_data)

@cache.memoize(expire=60*5, tag='place_details')
def get_place_details(place, search_data):
    time.sleep(0.1)
    place_details = populartimes.get_id(GOOGLE_MAPS_API_KEY, place["place_id"])
    distance = gmaps.distance_matrix(origins=place["geometry"]["location"], destinations=search_data["location"], mode="walking")
    place_details["distance"] = distance
    return place_details
