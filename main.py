from flask import Flask, request, jsonify
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from datetime import datetime
import swisseph as swe
import pytz

app = Flask(__name__)
swe.set_ephe_path(".")
swe.set_sid_mode(swe.SIDM_LAHIRI)  # Lahiri ayanamsha for Vedic astrology

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def get_sidereal_position(jd, planet):
    result, _ = swe.calc(jd, planet)
    return float(result[0])  # Longitude in degrees

def get_whole_sign_house(ascendant_sign_idx, planet_deg):
    """Whole Sign house system calculation"""
    planet_sign_idx = int(planet_deg // 30)
    return (planet_sign_idx - ascendant_sign_idx) % 12 + 1

def get_astrology_data(name, dob, tob, place):
    try:
        # Geocoding and timezone handling
        geolocator = Nominatim(user_agent="astroGPT")
        location = geolocator.geocode(place)
        if not location:
            return {"error": "Invalid place name. Try a nearby city."}

        lat, lon = location.latitude, location.longitude
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if not timezone_str:
            return {"error": "Timezone not found."}

        # Birth time conversion to UT
        tz = pytz.timezone(timezone_str)
        dt = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
        dt = tz.localize(dt)
        dt_ut = dt.astimezone(pytz.utc)
        
        # Julian day calculation
        jd = swe.julday(
            dt_ut.year, 
            dt_ut.month, 
            dt_ut.day,
            dt_ut.hour + dt_ut.minute/60.0 + dt_ut.second/3600.0
        )

        # Calculate Ascendant and zodiac sign
        cusps, ascmc = swe.houses(jd, lat, lon)  # Get ascendant
        ascendant = float(ascmc[0])
        ascendant_sign_idx = int(ascendant // 30)
        ascendant_sign = ZODIAC_SIGNS[ascendant_sign_idx]

        # Planetary positions
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

        for planet_name, code in planet_codes.items():
            deg = get_sidereal_position(jd, code)
            positions[planet_name] = round(deg, 2)
            houses[planet_name] = get_whole_sign_house(ascendant_sign_idx, deg)

        # Calculate Ketu (180° from Rahu)
        ketu_deg = (positions["Rahu"] + 180) % 360
        positions["Ketu"] = round(ketu_deg, 2)
        houses["Ketu"] = get_whole_sign_house(ascendant_sign_idx, ketu_deg)

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