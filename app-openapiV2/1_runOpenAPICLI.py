import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OUTPUT_DIR = os.getenv("OUTPUT_DIR")
OPENAPI_SPEC_PATH = os.getenv("OPENAPI_SPEC_PATH")

if not OUTPUT_DIR:
    raise ValueError("OUTPUT_DIR environment variable is not set")
if not OPENAPI_SPEC_PATH:
    raise ValueError("OPENAPI_SPEC_PATH environment variable is not set")

def generate_java_code(openapi_spec_path, output_dir):
    """
    Generate Java code from the OpenAPI specification.

    :param openapi_spec_path: Path to the OpenAPI specification file.
    :param output_dir: Directory where the generated code will be saved.
    """
    if not os.path.exists(openapi_spec_path):
        raise FileNotFoundError(f"OpenAPI spec file not found: {openapi_spec_path}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get environment variables for additional properties
    additional_properties = {
        "apiPackage": os.getenv("API_PACKAGE", "com.sc.banking.deposit.account.api"),
        "modelPackage": os.getenv("MODEL_PACKAGE", "com.sc.banking.deposit.account.model"),
        "basePackage": os.getenv("BASE_PACKAGE", "com.sc.banking.deposit.account"),
        "configPackage": os.getenv("CONFIG_PACKAGE", "com.sc.banking.deposit.account.config"),
        "invokerPackage": os.getenv("INVOKER_PACKAGE", "com.sc.banking.deposit.account.invoker"),
        "groupId": os.getenv("GROUP_ID", "com.sc.banking.deposit.account"),
        "artifactId": os.getenv("ARTIFACT_ID", "process-api-account-casa"),
        "version": os.getenv("VERSION", "1.0.0"),
        "springCloudVersion": os.getenv("SPRING_CLOUD_VERSION", "3.1.4"),
        "delegatePattern": os.getenv("DELEGATE_PATTERN", "true")
    }

    # Convert the dictionary to a comma-separated string
    additional_properties_str = ",".join(f"{key}={value}" for key, value in additional_properties.items())

    # Build the command
    command = [
        "openapi-generator-cli", "generate",
        "-i", openapi_spec_path,
        "-g", "spring",
        "-o", output_dir,
        "--template-dir", "/Users/samsundarkavala/Downloads/lab/openai/app-openapiV2/template",
        #"--ignore-file-override", ".openapi-generator-ignore",  # Add this line
        #"--openapi-generator-ignore-list", "src/main/java/com/sc/banking/deposit/account/model/*.java,!src/main/java/com/sc/banking/deposit/account/model/*Attribute*.java",
        "--additional-properties", additional_properties_str
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Java code generated successfully in: {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while generating Java code: {e}")

if __name__ == "__main__":
    generate_java_code(OPENAPI_SPEC_PATH, OUTPUT_DIR)
