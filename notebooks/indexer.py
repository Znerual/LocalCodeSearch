
import ast

def extract_functions_classes_comments(filename):
    with open(filename, "r") as f:
        file = f.read()
        tree = ast.parse(file)

    functions = []
    classes = []
    comments = []
    comments_by_function = {}
    comments_by_class = {}

    current_class_name = None
    current_func_name = None

    for node in tree.body:
        # node is a function
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            func_body = ast.get_source_segment(file, node).strip() # get code
            docstring = ast.get_docstring(node)
            if docstring:
                functions.append((func_name, func_body, docstring.strip(), node.lineno, node.end_lineno))
            else:
                functions.append((func_name, func_body, None))
            current_func_name = func_name
            current_class_name = None
            if current_func_name not in comments_by_function:
                comments_by_function[current_func_name] = []
                
            # iterate over subnodes to find comments
            for subnode in node.body:
                if isinstance(subnode, ast.Expr) and isinstance(subnode.value, ast.Str):
                    comment_text = subnode.value.s.strip()
                    comments_by_function[current_func_name].append(comment_text)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            comment_text = node.value.s.strip()
            if current_func_name:
                comments_by_function[current_func_name].append(comment_text)
            elif current_class_name:
                class_dict = comments_by_class.setdefault(current_class_name, {})
                class_dict[current_func_name].append(comment_text)
            else:
                comments.append(comment_text)
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            class_body = []
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef):
                    func_name = subnode.name
                    func_body = ast.get_source_segment(file, subnode).strip()
                    docstring = ast.get_docstring(subnode)
                    if docstring:
                        functions.append((class_name + "." + func_name, func_body, docstring.strip(), subnode.lineno, subnode.end_lineno))
                    else:
                        functions.append(("{}.{}".format(class_name, func_name), func_body, None, subnode.lineno, subnode.end_lineno))
                    current_func_name = func_name
                    current_class_name = class_name
                    if class_name not in comments_by_class:
                        comments_by_class[class_name] = {}
                    if current_func_name not in comments_by_class[class_name]:
                        comments_by_class[class_name][current_func_name] = []
                        
                    # iterate over subnodes to find comments
                    for subsubnode in subnode.body:
                        breakpoint()
                        if isinstance(subsubnode, ast.Expr) and isinstance(subsubnode.value, ast.Str):
                            comment_text = subsubnode.value.s.strip()
                            comments_by_class[class_name][current_func_name].append(comment_text)
                elif isinstance(subnode, ast.Expr) and isinstance(subnode.value, ast.Str):
                    comment_text = subnode.value.s.strip()
                    if current_func_name:
                        comments_by_function[current_func_name].append(comment_text)
                    elif current_class_name:
                        class_dict = comments_by_class.setdefault(current_class_name, {})
                        class_dict[current_func_name].append(comment_text)
                else:
                    class_body.append(ast.get_source_segment(file, subnode).strip())
            classes.append((class_name, "\n".join(class_body)))
            current_func_name = None
            current_class_name = None

    # Convert comments_by_function and comments_by_class dictionaries to lists of tuples
    comments_by_function = [(func_name, comments) for func_name, comments in comments_by_function.items()]
    comments_by_class = [(class_name, funcs) for class_name, funcs in comments_by_class.items()]

    return functions, classes, comments, comments_by_function, comments_by_class


# Function to extract imported modules that are used inside the function
def extract_imports(filename):
    with open(filename, "r") as f:
        tree = ast.parse(f.read())

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.add("{}.{}".format(node.module, alias.name))

    return list(imports)

if __name__ == "__main__":
    # Example usage
    filename = "/home/ruzickal/Code/Fingerprints/fp-research/fp-research/fingerprint/Essential/Config.py"
    functions, classes, comments, comments_by_function, comments_by_class = extract_functions_classes_comments(filename)
    imports = extract_imports(filename)
    print("Functions:", functions)
    print("Comments:", comments)
    print("Classes:", classes)
    print("Imports:", imports)
    print("Comments by function:", comments_by_function)
    print("Comments by class:", comments_by_class)
