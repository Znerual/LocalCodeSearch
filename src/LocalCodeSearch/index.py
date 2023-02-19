

import fnmatch
import os
import hashlib
import pymongo
import argparse
import logging

from nbconvert import PythonExporter
from nbconvert.preprocessors import RegexRemovePreprocessor

from database import project_dict, class_dict, function_dict, code_files_dict, other_files_dict, Class_entry, Function_entry, update_class_entry_code_file_id_checksum, update_function_entry_code_file_id_checksum, init_database
from parser import _process_python_code, _process_other_file

logger = logging.getLogger(__name__)

magic_preprocessor = RegexRemovePreprocessor(
    patterns=[r'^%%\w*\n', r'^%\w*\s']
)
exporter = PythonExporter(preprocessors=[magic_preprocessor])
exporter.exclude_input_prompt = True

def _get_package_name(package_path):
    folder_name = os.path.basename(package_path)
    if os.path.isfile(os.path.join(package_path, "__init__.py")):
        return folder_name
    return None


def _get_text_checksum(code):
    return hashlib.md5(code.encode()).hexdigest()

def _get_function_checksum(function_entry:Function_entry):
    text = f"{function_entry.name}{''.join(function_entry.imports)}{function_entry.code}{''.join(function_entry.imports)}{''.join(function_entry.imports_aliases)}{function_entry.docstring}{''.join(function_entry.comments)}{function_entry.summary}"
    return _get_text_checksum(text)

def _get_class_checksum(class_entry:Class_entry):
    text = f"{class_entry.name}{''.join(class_entry.imports)}{''.join([str(id) for id in class_entry.function_ids])}{''.join(class_entry.comments)}{class_entry.code}{class_entry.summary}"
    return _get_text_checksum(text)

def _get_checksum(file_path, file_name):
    # Read file content
    with open(os.path.join(file_path, file_name), "rb") as f:
        file_content = f.read()
    
    # Calculate checksum
    checksum = hashlib.md5(file_content).hexdigest()
    return checksum
 
         
def _update_functions(db, code_file, functions: list[Function_entry]):
    functions_db = db["code_functions"]

        
    # get functions from the database
    function_ids = code_file["function_ids"]
    saved_functions = [f for f in functions_db.find({"_id": {"$in": function_ids}})]
    saved_functions_names = [f["name"] for f in saved_functions]
    saved_functions_checksums = [f["checksum"] for f in saved_functions]
    
    # iterate over functions and see whether they got changed
    for function_entry in functions:
        function_index = None
        if function_entry.name in saved_functions_names:
          
            function_index = saved_functions_names.index(function_entry.name)
            function_checksum = _get_function_checksum(function_entry)
            if function_checksum == saved_functions_checksums[function_index]:
                continue
        
        # function was changed or does not exist
        if function_index is not None:
            function_id = function_ids[function_index]
            functions_db.update_one({"_id": function_id}, {"$set": function_dict(*function_entry)})
        else:
            new_function_entry = update_function_entry_code_file_id_checksum(function_entry, code_file["_id"], _get_function_checksum(function_entry))
            function_id = functions_db.insert_one(function_dict(*new_function_entry)).inserted_id
            function_ids.append(function_id)
            
    return function_ids
            
def _update_classes(db, code_file, classes: list[Class_entry]):
    # classes = [(name, imports, function_ids, comments, code, summary)]
    
    # get classes from the database
    class_ids = code_file["class_ids"]
    classes_db = db["code_classes"]
    saved_classes = classes_db.find({"_id": {"$in": class_ids}})
    saved_classes_names = [c["name"] for c in saved_classes]
    saved_classes_checksums = [c["checksum"] for c in saved_classes]
    
    # iterate over classes and see whether it was changed
    for class_entry in classes:
        class_index = None
        if class_entry.name in saved_classes_names:
            
            class_index = saved_classes_names.index(class_entry.name)
            class_checksum = _get_class_checksum(class_entry)
            if class_checksum == saved_classes_checksums[class_index]:
                continue
        
        # class was changed or does not exist
        if class_index is None:
            new_class_entry = update_class_entry_code_file_id_checksum(class_entry, code_file["_id"], _get_class_checksum(class_entry))
            class_ids.append(classes_db.insert_one(class_dict(*new_class_entry)).inserted_id)
        else:
            classes_db.update_one({"_id": class_ids[class_index]}, {"$set": class_dict(*class_entry)})
            
    return class_ids
            
def _update_python_code_file(db, project_id, code_file_id, checksum, file_path, file_name, package_name, module_level_imports, comments, classes, functions_by_class, comments_by_class,  functions, comments_by_function):
    # calculate checksum if not provided
    if checksum is None:
        checksum = _get_checksum(file_path, file_name)
    
    code_files = db["code_files"]
    
    if code_file_id is None:
        logger.debug("Inserting new code file for file {} in package {}".format(file_name, package_name))
        code_file_id = code_files.insert_one(code_files_dict(project_id, package_name, file_path, file_name, checksum, summary="", class_ids=[], function_ids=[], comments=comments)).inserted_id
    
    code_file = code_files.find_one({"_id": code_file_id})
    
        
    # create list of function_entries
    function_entries = [Function_entry(code_file_id, checksum=None,name=f[0], code=f[1], imports=list(f[3].keys()) + list(module_level_imports.keys()), imports_aliases=list(f[3].values()) + list(module_level_imports.values()), docstring=f[2], comments=comments_by_function[f[0]], summary="", line_start=f[4], line_end=f[5]) for f in functions]
    new_global_function_ids = []
    if len(function_entries) > 0:
        new_global_function_ids = _update_functions(db, code_file, function_entries)
        logger.debug("Updated {} functions for file {} in package {}".format(len(function_entries), file_name, package_name))

    # create class function entries
    new_class_function_ids = {}
    for class_name, _ in classes:
        class_function_entries = [Function_entry(code_file_id, checksum=None,name=f[0], code=f[1], imports=list(f[3].keys()) + list(module_level_imports.keys()), imports_aliases=list(f[3].values()) + list(module_level_imports.values()), docstring=f[2], comments=comments_by_class[class_name][f[0]], summary="", line_start=f[4], line_end=f[5]) for f in functions_by_class.setdefault(class_name, [])]
        if len(class_function_entries) > 0:
            new_class_function_ids[class_name] = _update_functions(db, code_file, class_function_entries)
            logger.debug("Updated {} functions for class {} in file {} in package {}".format(len(class_function_entries), class_name, file_name, package_name))
    # create list of class entries
    new_class_ids = []
    if len(classes) > 0:
        class_entries = [Class_entry(code_file_id, checksum=None, name=c[0],function_ids=new_class_function_ids.setdefault(c[0], []),  imports=module_level_imports, comments=comments_by_class.setdefault(c[0], {}).setdefault("", []), summary="") for c in classes]  
        new_class_ids = _update_classes(db, code_file, class_entries)
        logger.debug("Updated {} classes for file {} in package {}".format(len(class_entries), file_name, package_name))
        
    # update database entry
    new_code_file_dict = code_files_dict(project_id, package_name, file_path, file_name, checksum, summary="", class_ids=new_class_ids, function_ids=new_global_function_ids, comments=comments)
    del new_code_file_dict["creation_date"]
    code_files.update_one({"_id": code_file_id}, {"$set": new_code_file_dict})
    logger.debug("Updated code file {} to {} in package {}".format(file_name, new_code_file_dict, package_name))
    
def _update_other_file(db, project_id, code_file_id, checksum, file_path, file_name, package_name, file_content_filtered):
    # calculate checksum if not provided
    if checksum is None:
        checksum = _get_checksum(file_path, file_name)
    
    code_files = db["code_files"]
    
    # update database entry
    filter_query = {"_id": code_file_id}
    update = {"$set": other_files_dict(project_id, package_name, file_path, file_name, checksum, file_content_filtered)}
    code_files.update_one(filter_query, update)

def _update_file(db, project_id, code_file_id, checksum, folder_path, file_name, package_name, included_file_types=["Dockerfile", "*.toml", "*.md", "*.cfg"]):
    if file_name.endswith(".py"):
      
        with open( os.path.join(folder_path, file_name), "r") as f:
            file_content = f.read()
        logger.debug("Updating file: {}".format(os.path.join(folder_path, file_name)))
        result = _process_python_code(file_content)
        
        if result is None:
            logger.info("Could not process file: {}".format(os.path.join(folder_path, file_name)))
            return
        
        module_level_imports, comments, classes, functions_by_class, comments_by_class,  functions, comments_by_function = result
        _update_python_code_file(db, project_id, code_file_id, checksum, folder_path, file_name, package_name, module_level_imports, comments, classes, functions_by_class, comments_by_class,  functions, comments_by_function)
    elif file_name.endswith(".ipynb"):
       
        with open(os.path.join(folder_path, file_name)) as f:
            file_content, resources = exporter.from_file(f)
        logger.debug("Updating file: {}".format(os.path.join(folder_path, file_name)))
        result = _process_python_code(file_content)
        if result is None:
            logger.info("Could not process file: {}".format(os.path.join(folder_path, file_name)))
            return
        
        module_level_imports, comments, classes, functions_by_class, comments_by_class,  functions, comments_by_function = result
        _update_python_code_file(db, project_id, code_file_id, checksum, folder_path, file_name, package_name, module_level_imports, comments, classes, functions_by_class, comments_by_class,  functions, comments_by_function)
    for pattern in included_file_types:
        if fnmatch.fnmatch(file_name, pattern):
            with open(os.path.join(folder_path, file_name), "r") as f:
                file_content = f.read()
            filtered_content = _process_other_file(file_content)
            _update_other_file(db, project_id, code_file_id, checksum, folder_path, file_name, package_name, filtered_content)
            
    
        
def _update_file_check(db, project_name, root_dir, file_path, file_name):
    # Check if file is already in the database
    project = db["projects"].find_one({"name": project_name, "root_dir": root_dir})
    
    if project:
        project_id = project["_id"]
        logger.debug("Found project in database: {} with id {}".format(project_name, project_id))
        code_file = db["code_files"].find_one({"project_id": project_id, "file_path": file_path, "file_name": file_name})
        if code_file:
            saved_checksum = code_file["checksum"]
            new_checksum = _get_checksum(file_path, file_name)
            if new_checksum == saved_checksum:
                logger.debug("File {} already in database with checksum {} and did not change".format(file_name, new_checksum))
                return False, project_id, code_file["_id"], new_checksum
            else:
                logger.debug("File {} already in database with checksum {} but changed to {}".format(file_name, saved_checksum, new_checksum))
                return True, project_id, code_file["_id"], new_checksum
        else:
            return True, project_id, None, None
        
    # create project
    project_id = db["projects"].insert_one(project_dict(project_name, root_dir)).inserted_id
    logger.debug("Created project in database: {} with id {}".format(project_name, project_id))
    return True, project_id, None, None

def crawl_files(db, top_package_name, root_dir, package_name=None, exclude_folders=[]):
    #if package_name is None:
    #    package_name = os.path.basename(root_dir)
    subfolders = []
    src_dir = os.path.join(root_dir, "src")
    if os.path.isdir(src_dir):
        subfolders.append(src_dir)
        
        # set top package name to parent of src folder
        if top_package_name is None:
            top_package_name = root_dir
            
    tests_dir = os.path.join(root_dir, "tests")
    if os.path.isdir(tests_dir):
        subfolders.append(tests_dir)
    notebooks_dir = os.path.join(root_dir, "notebooks")
    if os.path.isdir(notebooks_dir):
        subfolders.append(notebooks_dir)
        
    subfolders += [os.path.join(root_dir, f) for f in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, f)) and f not in ["src", "tests", "notebooks"] and f not in exclude_folders]
    for file_path in subfolders:
        # a or b returns a if a is True, else returns b.
        # a and b returns b if a is True, else returns a.
        package_name = _get_package_name(file_path) or package_name
        top_package_name = top_package_name or (package_name and os.path.basename(os.path.dirname(file_path))) 
        crawl_files(db, top_package_name, file_path, package_name=package_name)
        logger.debug("Crawling folder: " + file_path + " ...")
        for file_name in os.listdir(file_path):
            update_required, project_id, code_file_id, checksum = _update_file_check(db, top_package_name, root_dir, file_path, file_name)
            if update_required:
                _update_file(db, project_id, code_file_id, checksum, file_path, file_name, package_name)
            
                
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Crawl a project and store the code files in a database.')
    parser.add_argument('root_folder', type=str, help='The root folder to start the crawl.')
    parser.add_argument('--db_host', type=str, help='The host of the database.', default="localhost")
    parser.add_argument('--db_port', type=int, help='The port of the database.', default=27017)
    parser.add_argument('--exclude_folders', nargs='*', type=str, help='A list of folders to exclude.', default=[])
    args = parser.parse_args()
    
    log_file = logging.FileHandler("crawl.log")
    console = logging.StreamHandler()
    logger.addHandler(log_file)
    logger.addHandler(console)
    logger.setLevel(logging.DEBUG)
    
    client, db = init_database(args.db_host, args.db_port)
    logger.info("Crawling files in %s" % args.root_folder)
    crawl_files(db, None, args.root_folder, exclude_folders=args.exclude_folders)
    
    client.close()