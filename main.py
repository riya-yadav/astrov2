from flask import Flask, request, jsonify
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from datetime import datetime
import swisseph as swe
import pytz

app = Flask(__name__)
swe.set_ephe_path(".")
swe.set_sid_mode(swe.SIDM_LAHIRI)

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def get_sidereal_position(jd, planet):
    lon_tuple = swe.calc(jd, planet)
    return float(lon_tuple[0])  # ✅ always a float

def get_house_number(lagna_deg, planet_deg):
    relative_deg = (planet_deg - lagna_deg) % 360
    return int(relative_deg // 30) + 1

def get_astrology_data(name, dob, tob, place):
    try:
        geolocator = Nominatim(user_agent="astroGPT")
        location = geolocator.geocode(place)
        if not location:
            return {"error": "Invalid place name. Try a nearby city."}

        lat, lon = location.latitude, location.longitude
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if not timezone_str:
            return {"error": "Timezone not found."}

        tz = pytz.timezone(timezone_str)
        dt = tz.localize(datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M"))
        jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)

        # Ascendant and sign
        ascendant = float(swe.houses(jd, lat, lon)[0][0])  # ✅ ensure float
        ascendant_sign_index = int(ascendant // 30)
        ascendant_sign = ZODIAC_SIGNS[ascendant_sign_index]

        # Planet positions and houses
        planet_codes = {
            "Sun": swe.SUN,
            "Moon": swe.MOON,
            "Mars": swe.MARS,
            "Mercury": swe.MERCURY,
            "Jupiter": swe.JUPITER,
            "Venus": swe.VENUS,
            "Saturn": swe.SATURN,
            "Rahu": swe.MEAN_NODE
        }

        positions = {}
        houses = {}

        for name, code in planet_codes.items():
            deg = get_sidereal_position(jd, code)  # ✅ float
            positions[name] = round(deg, 2)
            houses[name] = get_house_number(ascendant, deg)

        # Add Ketu
        ketu_deg = (positions["Rahu"] + 180) % 360
        positions["Ketu"] = round(float(ketu_deg), 2)
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