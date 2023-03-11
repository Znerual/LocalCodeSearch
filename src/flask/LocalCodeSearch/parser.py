import ast_comments
import re

import logging

logger = logging.getLogger(__name__)

class SensitiveDataVisitor(ast_comments.NodeVisitor):
    def __init__(self, sensitive_strings):
        super().__init__()
        self.sensitive_strings = sensitive_strings
    def visit_Assign(self, node):
        for target in node.targets:
            # check variable assignment
            if isinstance(target, ast_comments.Name):
                for sensitive_string in self.sensitive_strings:
                    if sensitive_string in target.id.lower():
                        for value in ast_comments.walk(node.value):
                            if isinstance(value, ast_comments.Str):
                                logger.info(f"Possible sensitive data found on line {value.lineno}: with {target.id} = {value.s}")
                                value.s = "FILTERED"
                                
            # check attribute assignment
            elif isinstance(target, ast_comments.Attribute):
                for sensitive_string in self.sensitive_strings:
                    if sensitive_string in target.attr.lower():
                        for value in ast_comments.walk(node.value):
                            if isinstance(value, ast_comments.Str):
                                logger.info(f"Possible sensitive data found on line {value.lineno}: {target.value.id}.{target.attr} = {value.s}")
                                value.s = "FILTERED"
                                
            # Check dictionary assignments
            elif isinstance(target, ast_comments.Subscript) and isinstance(target.value, ast_comments.Name) and isinstance(target.ctx, ast_comments.Load) and isinstance(target.slice.value, str):
                
                for sensitive_string in self.sensitive_strings:
                    if sensitive_string in target.slice.value.lower():
                        #if isinstance(node.value, ast_comments.Str):
                        for value in ast_comments.walk(node.value):
                            if isinstance(value, ast_comments.Str):
                                logger.info(f"Possible sensitive data found on line {target.value.lineno}: {target.value.id}[{target.slice.value}] = {node.value.s}")
                                node.value.s = "FILTERED"
        
        self.generic_visit(node)
               
class ImportsVisitor(ast_comments.NodeVisitor):
    def __init__(self):
        self.imports = {}
        self.scope = set()

    def visit_Import(self, node):
        if self.scope:
            for alias in node.names:
               self.imports[alias.name] = alias.asname or alias.name

    def visit_ImportFrom(self, node):
        if self.scope:
            module = node.module or ""
            for alias in node.names:
                name = alias.name
                asname = alias.asname or name
                full_name = f"{module}.{name}" if module else name
                self.imports[full_name] = asname

    def visit_FunctionDef(self, node):
        self.scope.add(node.name)
        self.generic_visit(node)
        if node.name in self.scope:
            self.scope.remove(node.name)


    def visit_ClassDef(self, node):
        self.scope.add(node.name)
        self.generic_visit(node)
        if node.name in self.scope:
            self.scope.remove(node.name)

    def visit_Call(self, node):
        if isinstance(node.func, ast_comments.Name):
            self.scope.add(node.func.id)
            self.generic_visit(node)
            if node.func.id in self.scope:
                self.scope.remove(node.func.id)
        elif isinstance(node.func, ast_comments.Attribute) and isinstance(node.func.value, ast_comments.Name):
            self.scope.add(node.func.value.id)
            self.generic_visit(node)
            if node.func.value.id in self.scope:
                self.scope.remove(node.func.value.id)


def _process_python_code(file_content):
    try:
        tree = ast_comments.parse(file_content)
    except SyntaxError as e:
        logger.debug(f"Syntax error in file: {e}.\nFile content: {file_content}")
        return None
    # filter out sensitive data
    sensitive_strings = [
        "password",
        "pwd",
        "api_key",
        "secret",
        "token",
        "private_key",
        "access_key",
        "credit_card",
        "social_security_number",
        "personal_identification_number",
        "passport_number",
        "license_number"
    ]
    sensitive_data_visitor = SensitiveDataVisitor(sensitive_strings)
    sensitive_data_visitor.visit(tree)
    filtered_file = ast_comments.unparse(tree)
    filtered_tree = ast_comments.parse(filtered_file)
    lines = filtered_file.splitlines()
    
    # extract classes, functions, comments and imports
    functions = []
    comments_by_function = {}
    classes = []
    comments_by_class = {}
    functions_by_class = {}
    comments = []
    module_level_imports = {}
    current_class_name = None
    current_func_name = None

    for node in filtered_tree.body:
        
        if isinstance(node, ast_comments.Import):
            for alias in node.names:
                module_level_imports[alias.name] = alias.asname or alias.name
        
        elif isinstance(node, ast_comments.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.name
                asname = alias.asname or name
                full_name = f"{module}.{name}" if module else name
                module_level_imports[full_name] = asname

                
        # node is a function
        elif isinstance(node, ast_comments.FunctionDef):
            
            # get imports
            visitor = ImportsVisitor()
            visitor.scope.add(node.name)
            visitor.visit(node)
            
            # get function name
            func_name = node.name
            current_func_name = func_name
            current_class_name = None
            if current_func_name not in comments_by_function:
                comments_by_function[current_func_name] = []
            
            # get docstring and source code, append to the functions list
            docstring = ast_comments.get_docstring(node)
            if docstring:
                start_pos, end_pos = node.body[0].lineno - 1, node.body[0].end_lineno 
                func_body = "\n".join(lines[node.lineno:start_pos] + lines[end_pos:node.end_lineno])
                functions.append((func_name, func_body, docstring.strip(), visitor.imports, node.lineno, node.end_lineno))
            else:
                func_body = ast_comments.get_source_segment(filtered_file, node).strip() # get code
                functions.append((func_name, func_body, None, visitor.imports, node.lineno, node.end_lineno))
                
            # iterate over subnodes to find comments
            for subnode in node.body:
                if isinstance(subnode, ast_comments.Comment):
                    comment_text = subnode.value[1:].strip()
                    comments_by_function[current_func_name].append(comment_text)
       
       # free standing comments
        elif isinstance(node, ast_comments.Comment):
            comment_text = node.value[1:].strip()
            comments.append(comment_text)
            
        # classes
        elif isinstance(node, ast_comments.ClassDef):
            class_name = node.name

            current_class_name = class_name
            current_func_name = None
            
            class_body = []
            for subnode in node.body:
                if isinstance(subnode, ast_comments.FunctionDef):
                    
                    # get function name
                    func_name = subnode.name
                    current_func_name = func_name
                    current_class_name = class_name
                    if class_name not in comments_by_class:
                        comments_by_class[class_name] = {}
                    if current_func_name not in comments_by_class[class_name]:
                        comments_by_class[class_name][current_func_name] = []
                        
                    class_functions = functions_by_class.setdefault(class_name, [])
                        
                    # get imports
                    visitor = ImportsVisitor()
                    visitor.scope.add(subnode.name)
                    visitor.visit(subnode)
                    
                    # get docstring and source code, append to the functions list
                    docstring = ast_comments.get_docstring(subnode)
                    if docstring:
                        start_pos, end_pos = subnode.body[0].lineno - 1, subnode.body[0].end_lineno 
                        func_body = "\n".join(lines[subnode.lineno:start_pos] + lines[end_pos:subnode.end_lineno])
                        class_functions.append((func_name, func_body, docstring.strip(), visitor.imports, subnode.lineno, subnode.end_lineno))
                    else:
                        func_body = ast_comments.get_source_segment(filtered_file, subnode).strip()
                        class_functions.append((func_name, func_body, None, visitor.imports, subnode.lineno, subnode.end_lineno))
                    
                    # iterate over subnodes to find comments inside function
                    for subsubnode in subnode.body:
                        if isinstance(subsubnode, ast_comments.Comment):
                            comment_text = subsubnode.value[1:].strip()
                            comments_by_class[class_name][current_func_name].append(comment_text)
                            
                # iterate over subnodes to find comments inside class
                elif isinstance(subnode, ast_comments.Comment):
                    comment_text = subnode.value[1:].strip()
                    class_comments = comments_by_class.setdefault(current_class_name, {})
                    class_func_comments = class_comments.setdefault("", [])
                    class_func_comments.append(comment_text)
                    
                else:
                    class_body.append(ast_comments.get_source_segment(filtered_file, subnode).strip())
                    
            classes.append((class_name, "\n".join(class_body)))
            current_func_name = None
            current_class_name = None

    ## Convert comments_by_function and comments_by_class dictionaries to lists of tuples
    #comments_by_function = [(func_name, comments) for func_name, comments in comments_by_function.items()]
    #comments_by_class = [(class_name, funcs) for class_name, funcs in comments_by_class.items()]

    return module_level_imports, comments, classes, functions_by_class, comments_by_class,  functions, comments_by_function, filtered_file

def _process_other_file(file_content):
    # Define regular expressions to match authentication tokens and credentials
    
    # git lab 
    token_pattern = r'(https://[^:]+:)[^@]+(@.*)'
    username_password_pattern = r'(https://)([^:]+):([^@]+)@(.*)'

    # general configuration
    username_pattern = r'username\s*=\s*[^\s]+'
    password_pattern = r'password\s*=\s*[^\s]+'
    apikey_pattern = r'apikey\s*=\s*[^\s]+'

    combined_pattern = re.compile(f"{token_pattern}|{username_password_pattern}|{username_pattern}|{password_pattern}|{apikey_pattern}")

    # Replace token
    file_content_filtered = re.sub(combined_pattern, r'\g<1>[REPLACED]\g<2>', file_content)

    return file_content_filtered