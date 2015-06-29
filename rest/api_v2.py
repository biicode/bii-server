from bottle import Bottle
from biicode.server.rest.basic_http_auth_bottle import BasicHttpAuthBottle
from biicode.server.rest.bson_bottle import BsonBottle

class restV2(BasicHttpAuthBottle):

    store = None

    def set_store(self,store):
        self.store = store

 
app = restV2() 
    
@app.route('/whatVersion', method = "GET")
@app.route('/whatVersion/', method = "GET")
def whatVersion():
    return "V2"+str(app.store)
