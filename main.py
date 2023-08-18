from flask import Flask, request, jsonify
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import math
from bson.objectid import ObjectId
# import sqlite3

from flask_cors import CORS
from pymongo import MongoClient


fuzzy_logic_app = Flask(__name__)
CORS(fuzzy_logic_app, resources={r"/*": {"origins": "*"}})
client = MongoClient('mongodb://localhost:27017/')
db = client['hotelsDb']
collection = db['hotels']


def getRate(id):
    filter = {'_id': ObjectId(id)}
    res = collection.find_one(filter)
    cumulative = res['cumulative']
    val = cumulative/res['total_submits']
    newvalues = {'$set': {'rate': val}}
  
    collection.update_one(filter, newvalues)
    return val

def checkinv(id,inv):
  res=collection.find_one({'_id' : ObjectId(id)})
  print(res['invoices'])
  if inv in res['invoices']:
      return False
  else:
      return True




def addrate(rate, id,invnum):
    
    newvalues = {'$inc': {'cumulative': rate, 'total_submits': 1} ,'$push':{'invoices' : invnum} }
    filter = {'_id': ObjectId(id)}
    collection.update_one(filter, newvalues)
    
 


@fuzzy_logic_app.route("/", methods=["GET"])
def allHot():

    fina = []
    for x in collection.find():
        x['_id'] = str(x['_id'])
        fina.append(x)

    return jsonify({"allstuff": fina})


@fuzzy_logic_app.route("/<hotel_id>", methods=["GET"])
def getall(hotel_id):
    filter = {'_id': ObjectId(hotel_id)}

    x = collection.find_one(filter)
    x['_id'] = str(x['_id'])
    return jsonify({"onehotel": x})


@fuzzy_logic_app.route("/<hotel_id>", methods=["PUT"])
def homepage(hotel_id):
    req = request.get_json()


# Add input variable service
    service = ctrl.Antecedent(np.arange(0, 11), 'service')
    service['notgood'] = fuzz.trapmf(service.universe, [0, 0, 2, 4])
    service['tolerable'] = fuzz.trimf(service.universe, [3, 5, 8])
    service['excellent'] = fuzz.trimf(service.universe, [6, 10, 10])


# Add input variable food
    food = ctrl.Antecedent(np.arange(0, 11), 'food')
    food['foul'] = fuzz.trapmf(food.universe, [0, 0, 2, 3])
    food['good'] = fuzz.gaussmf(food.universe, 5, 1.5)
    food['delicious'] = fuzz.trimf(food.universe, [6, 10, 10])


# add cleanliness input var
    cleanliness = ctrl.Antecedent(np.arange(0, 11), 'cleanliness')
    cleanliness['low'] = fuzz.trapmf(cleanliness.universe, [0, 0, 3, 5])
    cleanliness['medium'] = fuzz.trimf(cleanliness.universe, [3, 5.5, 8])
    cleanliness['clean'] = fuzz.trimf(cleanliness.universe, [6, 10, 10])


# add price input var
    price = ctrl.Antecedent(np.arange(10, 251), 'price')
    price['cheap'] = fuzz.trapmf(price.universe, [10, 10, 50, 120])
    price['suitable'] = fuzz.gaussmf(price.universe, 120, 25)
    price['expensive'] = fuzz.trapmf(
        price.universe, [120, 200, math.inf, math.inf])


# output

    evaluation = ctrl.Consequent(np.arange(0, 11), 'evaluation')
    evaluation['verybad'] = fuzz.trimf(evaluation.universe, [0, 1, 3])
    evaluation['bad'] = fuzz.trimf(evaluation.universe, [2, 4, 6])
    evaluation['medium'] = fuzz.trimf(evaluation.universe, [4, 6, 8])
    evaluation['wonderful'] = fuzz.trimf(evaluation.universe, [7, 10, 10])


# Define the rules
# very bad
    rule1 = ctrl.Rule((service['notgood'] & food['foul'] & cleanliness['medium']
                      & price['expensive']) | cleanliness['low'], evaluation['verybad'])
    # bad
    rule2 = ctrl.Rule(
        (food['foul'] & service['notgood'] & cleanliness['medium']
         & (price['suitable'] | price['cheap']))
        | (food['foul'] & service['notgood'] & cleanliness['clean'] & (price['suitable'] | price['expensive']))
        | (food['foul'] & service['tolerable'] & price['expensive'] & (cleanliness['medium'] | cleanliness['clean']))
        | (food['foul'] & service['excellent'] & cleanliness['medium'] & price['expensive'])
        | ((food['good'] | food['delicious']) & service['notgood'] & (cleanliness['medium'] | cleanliness['clean']) & (price['expensive'] | price['suitable'])), evaluation['bad'])
# medium
    rule3 = ctrl.Rule(((food['foul'] | food['good'] | food['delicious']) & service['notgood'] & (cleanliness['clean'] | cleanliness['medium']) & price['cheap'])
                      | (food['delicious'] & service['tolerable'] & cleanliness['medium'] & (price['cheap'] | price['expensive'] | price['suitable']))
                      | (food['delicious'] & service['tolerable'] & cleanliness['clean'] & (price['suitable'] | price['expensive']))
                      | (food['foul'] & service['tolerable'] & (cleanliness['medium'] | cleanliness['clean']) & (price['cheap'] | price['suitable']))
                      | (food['good'] & (service['excellent'] | service['tolerable']) & cleanliness['medium'] & (price['expensive'] | price['suitable']))
                      | (food['good'] & (service['tolerable'] | service['excellent']) & cleanliness['clean'] & price['expensive'])
                      | (food['foul'] & service['excellent'] & cleanliness['medium'] & (price['cheap'] | price['suitable']))
                      | (food['foul'] & service['excellent'] & cleanliness['clean'] & (price['expensive'] | price['suitable']))
                      | (food['delicious'] & service['notgood'] & cleanliness['clean'] & price['suitable'])
                      | (food['delicious'] & service['excellent'] & cleanliness['medium'] & price['expensive']), evaluation['medium']
                      )
# wonderful
    rule4 = ctrl.Rule((food['good'] & (service['tolerable'] | service['excellent']) & (cleanliness['clean'] | cleanliness['medium']) & price['cheap'])
                      | (food['good'] & (service['excellent'] | service['tolerable']) & cleanliness['clean'] & price['suitable'])
                      | (food['delicious'] & service['excellent'] & cleanliness['medium'] & (price['cheap'] | price['suitable']))
                      | (food['delicious'] & service['excellent'] & cleanliness['clean'] & (price['cheap'] | price['expensive'] | price['suitable']))
                      | (food['foul'] & service['excellent'] & cleanliness['clean'] & price['cheap'])
                      | (food['delicious'] & service['tolerable'] & cleanliness['clean'] & price['cheap']), evaluation['wonderful']
                      )

    # rating.
    rating = ctrl.ControlSystem(rules=[rule1, rule2, rule3, rule4])
    # Evaluate the FIS
    rate_sys = ctrl.ControlSystemSimulation(rating)
    rate_sys.input['service'] = float(req["service"])
    rate_sys.input['food'] = float(req["food"])
    rate_sys.input['cleanliness'] = float(req["cleanliness"])
    rate_sys.input['price'] = float(req["price"])
    rate_sys.compute()
    rate_value = rate_sys.output['evaluation']
   
    print(f'the rate is : {rate_value:.2f}')
    if(checkinv(hotel_id,req['invoice'])):
        addrate(rate_value, hotel_id,req["invoice"])
        val1 = getRate(hotel_id)
    else:
         return {"err" : "duplicated invoice number"}
    
    
    # print(res)

    return {"your rate": rate_value, "current rate": val1}


if __name__ == "__main__":
    fuzzy_logic_app.run(debug=True)
