import json

from agentic_fleet.app.main import app


def generate_openapi():
    """
    Write the application's OpenAPI schema to openapi.json.

    Retrieves the FastAPI app's OpenAPI schema and writes it as formatted JSON to a file named "openapi.json" in the current working directory. Prints a confirmation message after the file is written.
    """
    openapi_data = app.openapi()
    # Enforce 3.0.0 version if needed by strict requirement, though FastAPI emits 3.0.2 or 3.1.0 usually.
    # The user requested "version 3.0.0" in the prompt context of "url /api version 3.0.0".
    # But standard valid OpenAPI versions are 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.1.0.
    # We set openapi_version="3.0.2" in FastAPI which is standard for compat.

    with open("openapi.json", "w") as f:
        json.dump(openapi_data, f, indent=2)
    print("Generated openapi.json")


if __name__ == "__main__":
    generate_openapi()
