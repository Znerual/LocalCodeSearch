from datetime import datetime
from collections import namedtuple

import pymongo


Class_entry = namedtuple("Class_entry", "code_file_id checksum name function_ids imports comments code summary", defaults=[[], [], [], "", ""])
Function_entry = namedtuple("Function_entry", "code_file_id checksum name code imports imports_aliases docstring comments summary line_start line_end", defaults=[[], [], "", "", [], "", 0, -1])

def update_function_entry_code_file_id_checksum(function_entry, code_file_id, checksum):
    return Function_entry(code_file_id, checksum, function_entry.name, function_entry.code, function_entry.imports, function_entry.imports_aliases, function_entry.docstring, function_entry.comments, function_entry.summary, function_entry.line_start, function_entry.line_end)

def update_class_entry_code_file_id_checksum(class_entry, code_file_id, checksum):
    return Class_entry(code_file_id, checksum, class_entry.name, class_entry.function_ids, class_entry.imports, class_entry.comments, class_entry.code, class_entry.summary)

def project_dict(name, root_dir, crawl_date=datetime.now()):
    return {"name": name, "root_dir" : root_dir, "crawl_date": crawl_date}

def class_dict(code_file_id, checksum, name, function_ids = [], imports=[], comments=[], code="", summary=""):
    return {"code_file_id": code_file_id, "checksum" : checksum, "name": name, "function_ids" : function_ids, "imports" : imports, "comments" : comments, "code": code, "summary" : summary}

def function_dict(code_file_id, checksum, name, code, imports=[], imports_aliases=[], docstring="", comments=[], summary="", line_start=0, line_end=-1):
    return {"code_file_id":  code_file_id, "checksum" : checksum, "name": name, "code": code, "imports" : imports, "imports_aliases" : imports_aliases, "docstring" : docstring, "comments" : comments,  "summary" : summary, "line_start": line_start, "line_end": line_end}

def code_files_dict(project_id, module, file_path, file_name, checksum, content, summary="", class_ids=[], function_ids=[], comments=[], modify_date=datetime.now(), creation_date=datetime.now(), crawl_date=datetime.now()):
    return {"project_id": project_id, "checksum" : checksum, "module" : module, "file_path" : file_path, "file_name" : file_name, "summary" : summary, "content" : content, "class_ids" : class_ids, "function_ids" : function_ids, "comments" : comments, "modify_date" : modify_date, "creation_date" : creation_date, "crawl_date" : crawl_date}

def other_files_dict(project_id, module, file_path, file_name, checksum, content, summary="", modify_date=datetime.now(), creation_date=datetime.now(), crawl_date=datetime.now()):
    return {"project_id": project_id, "module" : module, "file_path" : file_path, "file_name" : file_name, "checksum" : checksum, "summary" : summary, "content" : content, "modify_date" : modify_date, "creation_date" : creation_date, "crawl_date" : crawl_date}

def init_database(host="localhost", port=27017):
    client = pymongo.MongoClient(host, port)
    db = client["CodeIndex"]
    return client, db