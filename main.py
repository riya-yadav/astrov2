from flask import Flask, request, jsonify
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from datetime import datetime
import swisseph as swe
import pytz

app = Flask(__name__)

# Set Swiss Ephemeris path (if you have ephemeris files locally, else it downloads automatically)
swe.set_ephe_path(".")

# Set sidereal mode with Lahiri ayanamsa for Vedic astrology
swe.set_sid_mode(swe.SIDM_LAHIRI)

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def get_sidereal_position(jd, planet):
    # swe.calc returns a tuple: (longitude, latitude, distance, speed_long, speed_lat, speed_dist)
    lon_tuple = swe.calc(jd, planet)
    return float(lon_tuple[0])  # longitude in degrees

def get_house_number(lagna_deg, planet_deg):
    relative_deg = (planet_deg - lagna_deg) % 360
    return int(relative_deg // 30) + 1

def get_astrology_data(name, dob, tob, place):
    try:
        # Geocode place to get latitude and longitude
        geolocator = Nominatim(user_agent="astroGPT")
        location = geolocator.geocode(place)
        if not location:
            return {"error": "Invalid place name. Try a nearby city."}

        lat, lon = location.latitude, location.longitude

        # Find timezone from lat/lon
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if not timezone_str:
            return {"error": "Timezone not found."}

        tz = pytz.timezone(timezone_str)

        # Parse date and time of birth, localize to timezone
        dt = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
        dt = tz.localize(dt)

        # Convert to Universal Time (UT) for Swiss Ephemeris
        dt_ut = dt.astimezone(pytz.utc)

        # Calculate Julian Day in UT
        jd = swe.julday(dt_ut.year, dt_ut.month, dt_ut.day, dt_ut.hour + dt_ut.minute / 60.0 + dt_ut.second / 3600.0)

        # Calculate Ascendant (Lagna)
        houses_cusps, ascmc = swe.houses(jd, lat, lon)
        ascendant = float(ascmc[0])  # ascendant degree
        ascendant_sign_index = int(ascendant // 30)
        ascendant_sign = ZODIAC_SIGNS[ascendant_sign_index]

        # Planet codes to calculate
        planet_codes = {
            "Sun": swe.SUN,
            "Moon": swe.MOON,
            "Mars": swe.MARS,
            "Mercury": swe.MERCURY,
            "Jupiter": swe.JUPITER,
            "Venus": swe.VENUS,
            "Saturn": swe.SATURN,
            "Rahu": swe.MEAN_NODE  # North Node
        }

        positions = {}
        houses = {}

        # Calculate sidereal positions and houses
        for planet_name, code in planet_codes.items():
            deg = get_sidereal_position(jd, code)
            positions[planet_name] = round(deg, 2)
            houses[planet_name] = get_house_number(ascendant, deg)

        # Calculate Ketu (South Node) position and house
        ketu_deg = (positions["Rahu"] + 180) % 360
        positions["Ketu"] = round(ketu_deg, 2)
        houses["Ketu"] = get_house_number(ascendant, ketu_deg)

        return {
            "name": name,
            "place": place,
            "ascendant": round(ascendant, 2),
            "ascendant_sign": ascendant_sign,
            "planet_positions": positions,
            "planet_houses": houses
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    return jsonify(get_astrology_data(
        data.get("name", ""),
        data.get("dob", ""),
        data.get("tob", ""),
        data.get("place", "")
    ))

@app.route("/")
def home():
    return "🕉️ Vedic Astrology API is LIVE!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
