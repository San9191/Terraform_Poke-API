from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient
from bson import ObjectId
import os
import random
from flask.json.provider import DefaultJSONProvider 

# ==============================================
# Database Connection
# ==============================================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client.pokemon_registry
favorites_collection = db.favorites_poke

# ==============================================
# Flask App
# ==============================================

app = Flask(__name__)

# ======= JSON PROVIDER ==================

class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

app.json = CustomJSONProvider(app) 


# ==============================================
# Routes
# ==============================================

@app.route("/favorites_poke", methods=["GET"])
def get_favorites():
    favorites_poke = list(favorites_collection.find({}, {"_id": 0}))
    return jsonify({"favorites_poke": favorites_poke}), 200


@app.route("/pokemons", methods=["GET"])
def get_random_pokemon():
    try:
        resp = requests.get("https://pokeapi.co/api/v2/pokemon?limit=100")
        resp.raise_for_status()
        pokemon_list = resp.json()["results"]

        selected = random.choice(pokemon_list)

        details_resp = requests.get(selected["url"])
        details_resp.raise_for_status()
        details = details_resp.json()

        favorite_payload = {
            "name": details["name"],
            "height": details["height"],
            "weight": details["weight"],
            "base_experience": details["base_experience"]
        }

        if favorite_payload["base_experience"] < 100:
            return jsonify({"message": "Base experience too low"}), 400

        existing = favorites_collection.find_one({"name": favorite_payload["name"]})
        if existing:
            return jsonify({"message": "Favorite already exists!"}), 400

        favorites_collection.insert_one(favorite_payload)

        return jsonify({"message": "Favorite saved!", "favorite": favorite_payload}), 201

    except requests.RequestException as e:
        return jsonify({"message": f"Error fetching from PokeAPI: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/favorites_poke/name/<name>", methods=["DELETE"])
def delete_favorite_by_name(name):
    result = favorites_collection.find_one_and_delete({"name": {"$regex": f"^{name}$", "$options": "i"}})

    if not result:
        return jsonify({"message": "Favorite not found"}), 404

    
    return jsonify({"message": "Favorite deleted", "deleted": result}), 200


@app.route("/favorites_poke", methods=["POST"])
def add_favorite():
    data = request.get_json()

    try:
        name = data.get("name")
        height = data.get("height")
        weight = data.get("weight")
        base_exp = data.get("base_experience")

        if base_exp < 100:
            return jsonify({"message": "Base experience too low"}), 400

        if favorites_collection.find_one({"name": name}):
            return jsonify({"message": "Favorite already exists!"}), 400

        favorite = {
            "name": name,
            "height": height,
            "weight": weight,
            "base_experience": base_exp
        }

        favorites_collection.insert_one(favorite)
        return jsonify({"message": "Favorite saved!", "favorite": favorite}), 201

    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ==============================================
# Entry Point
# ==============================================

if __name__ == "__main__":
    app.run(port=5000, debug=True)
