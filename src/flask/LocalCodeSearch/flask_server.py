from flask import Flask, render_template, request, flash, redirect, url_for, session
#from flask_login import LoginManager
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from index import _update_file_check, _update_file
import os

app = Flask(__name__, static_url_path='/static', static_folder='./static')
app.secret_key = "super secret key"

ALLOWED_EXTENSIONS = {'txt', 'conf', 'yml', 'yaml', 'py', 'ipynb', 'Dockerfile', 'toml', 'md', 'cfg'}

app.config["MONGO_URI"] = os.getenv("MONGO_URL", "mongodb://localhost:27017/CodeIndex")
mongo = PyMongo(app)



def allowed_file(filename):
    for allowed_extension in ALLOWED_EXTENSIONS:
        if filename.lower().endswith(allowed_extension):
            return True
    return False

@app.route("/", methods=['GET', 'POST'])
def index():
    collection = mongo.db.code_files
    code_files = collection.find()
    
    file_names = {}
    #flash("You're at index")
    # check if post request has the file part
    if request.method == "POST":
        if "files" not in request.files and "file" not in request.files:
            print("No file part")
            return redirect(request.url)
        files = request.files.getlist('files')
        file = request.files["file"]
        print(files)
        print(file)
        # if the user did not select a file, we get an empty file without filename
        if (len(files) == 0 or files[0].filename == "") and file.filename == "":
            print("No selected file")
            return redirect(request.url)
        
        project_name = request.args.get("project", "Unknown")
        package_name = request.args.get("package", "Unknown")
        if file and file.filename != "":
            file_content = file.read().decode('utf-8')
            filename = secure_filename(file.filename)
            update_required, project_id, code_file_id, checksum = _update_file_check(mongo.db, project_name, "Upload", "Upload", filename, file_content)
            if update_required:
                _update_file(mongo.db, project_id, code_file_id, checksum, "Upload",filename, package_name, file_content)
            file_names[filename] = len(file_content)
            
        for lfile in files:
            if lfile and allowed_file(lfile.filename):
                filename = secure_filename(lfile.filename)
                file_content = lfile.read().decode('utf-8')
                update_required, project_id, code_file_id, checksum = _update_file_check(mongo.db, project_name, "Upload", "Upload", filename, file_content)
                if update_required:
                    _update_file(mongo.db, project_id, code_file_id, checksum, "Upload", filename, package_name, file_content)
                file_names[filename] = len(file_content)
            #return redirect(url_for(''))
        # TODO: Update databse with projectname, filename and file content
    #print(code_files)
    return render_template("index.html", code_files=code_files, file_names=file_names)


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

# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=os.environ.get("PORT", 3000))
