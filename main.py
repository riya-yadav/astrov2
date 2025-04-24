from flask import Flask, request, jsonify
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from datetime import datetime
import swisseph as swe
import pytz

app = Flask(__name__)
swe.set_ephe_path('.')

def get_astrology_data(name, dob, tob, place):
    try:
        geolocator = Nominatim(user_agent="astroGPT")
        location = geolocator.geocode(place)
        if not location:
            return {"error": "Invalid place name. Try a nearby city."}

        lat, lon = location.latitude, location.longitude
        tz_finder = TimezoneFinder()
        timezone_str = tz_finder.timezone_at(lat=lat, lng=lon)
        if timezone_str is None:
            return {"error": "Could not detect timezone. Try a larger city name."}

        tz = pytz.timezone(timezone_str)
        dt_obj = tz.localize(datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M"))

        jd = swe.julday(dt_obj.year, dt_obj.month, dt_obj.day, dt_obj.hour + dt_obj.minute / 60)
        planets = {}
        for planet in [swe.SUN, swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN]:
            lon = swe.calc_ut(jd, planet)[0][0]
            planets[swe.get_planet_name(planet)] = lon

        houses = swe.houses(jd, lat, lon)
        ascendant = houses[0][0]

        summary = f"""
        🔮 Name: {name}
        🪐 Place: {place}
        ☀️ Sun: {planets['Sun']:.2f}°
        🌙 Moon: {planets['Moon']:.2f}°
        🪐 Lagna (Ascendant): {ascendant:.2f}°
        🛕 More Graha positions: {planets}
        """
        return {"summary": summary, "planets": planets, "ascendant": ascendant}
    
    except Exception as e:
        return {"error": f"Server crashed: {str(e)}"}

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    result = get_astrology_data(
        data.get("name", ""),
        data.get("dob", ""),
        data.get("tob", ""),
        data.get("place", "")
    )
    return jsonify(result)

@app.route("/")
def home():
    return "🕉️ Pandit Ji API is LIVE!"

app.run(host="0.0.0.0", port=8080)
