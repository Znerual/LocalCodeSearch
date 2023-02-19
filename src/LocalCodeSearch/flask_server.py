from flask import Flask, render_template, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__, static_url_path='/static', static_folder='./static')
app.config["MONGO_URI"] = "mongodb://localhost:27017/CodeIndex"
mongo = PyMongo(app)

@app.route("/")
def index():
    collection = mongo.db.code_files
    code_files = collection.find()
    #print(code_files)
    return render_template("index.html", code_files=code_files)

@app.route('/search')
def search():
    
    # Get the form inputs
    form_inputs = {'file_name' : request.args.get('file_name'),
                   "functions" : request.args.get('functions'),
                   "classes" : request.args.get('classes'),
                   "docstring" : request.args.get('docstring'),
                   "comments" : request.args.get('comments'),
                   "content" : request.args.get('content')}
    
    print(form_inputs)
    query = {}
    
    for i in range(1, 7):
        option_name = f'option{i}'
        
        input_value = list(form_inputs.values())[i-1]
        option = request.args.get(option_name, 'Or')
       
        if input_value:
            input_value = input_value.strip()
            if option == 'Or':
                if "$or" in query:
                    query["$or"].append({list(form_inputs.keys())[i-1]: {'$regex': input_value, '$options': 'i'}})
                else:
                    query["$or"] = [{list(form_inputs.keys())[i-1]: {'$regex': input_value, '$options': 'i'}}]
               
            else:
                query[list(form_inputs.keys())[i-1]] = {'$regex': input_value, '$options': 'i'}
        

    print(query)
   
    
    results = mongo.db.code_files.aggregate([
        {
            "$lookup": {
                "from": "code_functions",
                "localField": "function_ids",
                "foreignField": "_id",
                "as" : "functions_info"
            }
        },
        {
            '$lookup': {
                'from': 'code_classes',
                'localField': 'class_ids',
                'foreignField': '_id',
                'as': 'classes'
            }
        },
        {
            "$addFields": {
                "functions_info": {
                    "$map": {
                        "input": "$functions_info",
                        "as": "function",
                        "in": "$$function.name"
                    }
                },
                "functions_comments" : {
                    "$map": {
                        "input": "$functions_info",
                        "as": "comments",
                        "in": "$$comments.comments"
                    }
                },
                "classes": {
                    "$map": {
                    "input": "$classes",
                    "as": "class",
                    "in": "$$class.name"
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 1,
                "file_name": 1,
                "path": 1,
                "functions": 1,
                "classes": 1,
                "docstring": 1,
                "comments": 1,
                "content": 1
            }
        },
        {
            "$match": query
        }
        
    ]
    )
    print(results)
    #results = list(collection.find(query))
    #return {'results': results}

    
    #print(query)
    #results = mongo.db.code_files.find({'file_name': {'$regex': query}})
    return render_template('results.html', results=results)

@app.route('/help')
def help():
    return render_template('index.html')

@app.route('/result_details')
def result_details():
    result_id = request.args.get('id')
    result = mongo.db.code_files.find_one({'_id': ObjectId(result_id)})
    return render_template('result_details.html', result=result)


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
    app.run(debug=True)
