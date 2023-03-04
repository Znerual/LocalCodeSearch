from flask import Flask, render_template, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

import os

app = Flask(__name__, static_url_path='/static', static_folder='./static')

#"mongodb://localhost:27017/CodeIndex"
app.config["MONGO_URI"] = os.environ["MONGO_URL"]
print("MONGO_URL = ", os.environ["MONGO_URL"])
mongo = PyMongo(app)

@app.route("/")
def index():
    collection = mongo.db.code_files
    code_files = collection.find()
    #print(code_files)
    return render_template("index.html", code_files=code_files)

@app.route('/search')
def search():
    
    query = {}
    packages_input = request.args.get('packages', None)
    if packages_input:
        query["$or"] = [{"imports": {'$regex': packages_input, '$options': 'i'}},
                        {"imports_aliases": {'$regex': packages_input, '$options': 'i'}}]
        
    content_input = request.args.get('content', None)
    if content_input:
        query["$and"] = [{"$or" : [{"code": {'$regex': content_input, '$options': 'i'}},
                                   {"docstring": {'$regex': content_input, '$options': 'i'}},
                                   {"comments": {'$elemMatch' : {'$regex': content_input, '$options': 'i'}}},
                                   {"summary": {'$regex': content_input, '$options': 'i'}}]}]
    
   
    
    
    #results = list(collection.find(query))
    #return {'results': results}

    
    #print(query)
    results = mongo.db.code_functions.find(query)
    return render_template('results.html', results=results)

@app.route('/help')
def help():
    return render_template('index.html')

@app.route('/result_details')
def result_details():
    code_file_id = request.args.get('id')
    print("In results details got code file id = ", code_file_id)
    code_file_entry = mongo.db.code_files.find_one({'_id': ObjectId(code_file_id)})
    project = mongo.db.projects.find_one({'_id': ObjectId(code_file_entry['project_id'])})
    functions = tuple([f for f in mongo.db.code_functions.find({'_id': {"$in" : code_file_entry["function_ids"]}})])
    print(len(functions))
    classes = mongo.db.code_classes.find({'_id': {"$in" : code_file_entry["class_ids"]}})
    class_functions = tuple([(cl, [f for f in mongo.db.code_functions.find({'_id': {"$in" : cl["function_ids"]}})]) for cl in classes])
    return render_template('result_details.html', code_file=code_file_entry, project=project, functions=functions, class_functions=class_functions)


# @app.route('/results')
# def results():
#     result_id = request.args.get('id')
#     print(result_id)
#     result = mongo.db.code_files.find_one({'_id': ObjectId(result_id)})
#     return render_template('results.html', result=result)

# @app.teardown_appcontext
# def close_mongo_connection(exception=None):
#     mongo.cx.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=os.environ.get("PORT", 3000))
