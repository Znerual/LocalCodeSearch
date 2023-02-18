from flask import Flask, render_template, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/CodeIndex"
mongo = PyMongo(app)

@app.route("/")
def index():
    collection = mongo.db.code_files
    code_files = collection.find()
    return render_template("index.html", code_files=code_files)

@app.route('/search')
def search():
    query = request.args.get('query')
    results = mongo.db.code_files.find({'file_name': {'$regex': query}})
    return render_template('search_results.html', results=results)

@app.route('/result_details')
def result_details():
    result_id = request.args.get('id')
    result = mongo.db.code_files.find_one({'_id': ObjectId(result_id)})
    return render_template('result_details.html', result=result)

# @app.teardown_appcontext
# def close_mongo_connection(exception=None):
#     mongo.cx.close()

if __name__ == "__main__":
    app.run(debug=True)
