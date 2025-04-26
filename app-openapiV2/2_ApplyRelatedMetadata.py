import json
import os
from dotenv import load_dotenv
import jpype
import jpype.imports
import sys
from pathlib import Path

# Get the current directory
current_dir = Path(__file__).parent.absolute()
javaparser_jar = str(current_dir / "javaparser-core-3.24.4.jar")

# Initialize JVM and import Java classes
try:
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[javaparser_jar])
        print("JVM started successfully")
    
    # Import Java classes after JVM is started
    from com.github.javaparser import StaticJavaParser
    from com.github.javaparser.ast.body import ClassOrInterfaceDeclaration
    from com.github.javaparser.ast import CompilationUnit, NodeList
    from com.github.javaparser.ast.expr import (
        Name, NormalAnnotationExpr, StringLiteralExpr, 
        MemberValuePair, FieldAccessExpr, NameExpr
    )
    from com.github.javaparser.ast.type import ClassOrInterfaceType
    from com.github.javaparser.ast.Modifier import Keyword
    print("JavaParser classes imported successfully")
except Exception as e:
    print(f"Error initializing JVM or importing JavaParser: {str(e)}")
    print(f"Make sure {javaparser_jar} exists")
    sys.exit(1)

# Load environment variables
load_dotenv()

OPENAPI_SPEC_PATH = os.getenv("OPENAPI_SPEC_PATH")
MODEL_PACKAGE = os.getenv("MODEL_PACKAGE")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

if not all([OPENAPI_SPEC_PATH, MODEL_PACKAGE, OUTPUT_DIR]):
    raise ValueError("Required environment variables are not set")

def find_schemas_with_related_objects(spec_path):
    """
    Parse OpenAPI spec and find schemas that have x-related-objects attribute.
    
    Args:
        spec_path (str): Path to OpenAPI specification file
    
    Returns:
        dict: Dictionary of schema names and their x-related-objects
    """
    try:
        with open(spec_path, 'r') as file:
            spec = json.load(file)
            
        schemas = spec.get('components', {}).get('schemas', {})
        related_schemas = {}
        
        for schema_name, schema_def in schemas.items():
            if 'x-related-objects' in schema_def:
                related_schemas[schema_name] = {
                    'x-related-objects': schema_def['x-related-objects']
                }
        
        return related_schemas
                
    except FileNotFoundError:
        print(f"Error: OpenAPI spec file not found at {spec_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in OpenAPI spec file")
        return None
    except Exception as e:
        print(f"Error parsing OpenAPI spec: {str(e)}")
        return None

def get_java_file_path(schema_name):
    """Convert schema name to Java file path"""
    package_path = MODEL_PACKAGE.replace('.', '/')
    return os.path.join(OUTPUT_DIR, "src/main/java", package_path, f"{schema_name}.java")

def create_field_access_expr(scope_name, field_name):
    """Create a FieldAccessExpr for enum values"""
    scope = NameExpr(scope_name)
    return FieldAccessExpr(scope, field_name)

def update_java_file(file_path, related_objects):
    """Update Java file with related object fields using JavaParser"""
    try:
        # Parse Java file
        with open(file_path, 'r') as file:
            content = file.read()
            
        cu = StaticJavaParser.parse(content)
        
        # Add imports if they don't exist
        imports_to_add = [
            "com.sc.banking.common.annotation.RelatedObject",
            "com.sc.banking.common.enums.ObjectType",
            "com.sc.banking.common.enums.FetchType",
            "com.fasterxml.jackson.annotation.JsonIgnore",
            "java.util.List"
        ]
        for import_stmt in imports_to_add:
            if not any(imp.getNameAsString() == import_stmt for imp in cu.getImports()):
                cu.addImport(import_stmt)
        
        # Get the main class
        main_class = cu.getType(0)
        if not isinstance(main_class, ClassOrInterfaceDeclaration):
            raise Exception("No class declaration found in file")
        
        # Add related object fields
        for obj in related_objects:
            field_name = obj['name']
            base_type = obj['type']
            relation = obj.get('relation', 'OneToOne')  # Default to OneToOne if not specified
            
            # Determine field type based on relation
            if relation == 'OneToMany':
                field_type = f"List<{base_type}>"
            else:
                field_type = base_type
            
            # Check if field already exists
            existing_field = main_class.getFieldByName(field_name)
            if not existing_field.isPresent():
                # Create new field with private modifier
                field = main_class.addField(field_type, field_name, [Keyword.PRIVATE])
                
                # Add JsonIgnore annotation
                field.addAnnotation("JsonIgnore")
                
                # Create the RelatedObject annotation
                name = Name("RelatedObject")
                pairs = NodeList()
                
                # Create field access expressions for enum values
                object_expr = create_field_access_expr("ObjectType", obj['objectType'])
                fetch_expr = create_field_access_expr("FetchType", obj['fetchType'])
                
                # Create member value pairs for the annotation
                pairs.add(MemberValuePair("object", object_expr))
                pairs.add(MemberValuePair("fetchType", fetch_expr))
                
                # Create annotation with NodeList
                annotation = NormalAnnotationExpr(name, pairs)
                
                # Add annotation to field
                field.addAnnotation(annotation)
                
                # Generate getter method
                getter_name = f"get{field_name[0].upper()}{field_name[1:]}"
                getter_method = f"""
    @JsonIgnore
    public {field_type} {getter_name}() {{
        return this.{field_name};
    }}"""
                main_class.addMember(StaticJavaParser.parseBodyDeclaration(getter_method))
                
                # Generate setter method
                setter_name = f"set{field_name[0].upper()}{field_name[1:]}"
                setter_method = f"""
    @JsonIgnore
    public void {setter_name}({field_type} {field_name}) {{
        this.{field_name} = {field_name};
    }}"""
                main_class.addMember(StaticJavaParser.parseBodyDeclaration(setter_method))
                
                print(f"Added private {relation} field {field_name} with RelatedObject and JsonIgnore annotations, and getter/setter methods")
        
        # Write back formatted code
        with open(file_path, 'w') as file:
            file.write(str(cu))
            
        print(f"Updated {file_path}")
        
    except Exception as e:
        print(f"Error updating Java file {file_path}: {str(e)}")
        raise

def main():
    related_schemas = find_schemas_with_related_objects(OPENAPI_SPEC_PATH)
    
    if related_schemas:
        for schema_name, details in related_schemas.items():
            java_file_path = get_java_file_path(schema_name)
            update_java_file(java_file_path, details['x-related-objects'])

if __name__ == "__main__":
    main()
