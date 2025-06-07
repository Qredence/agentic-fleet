```mermaid
graph TD
    A[main.py:main()] --> B(core.config.logging:setup_global_logging());
    B --> C(config.config_manager:validate_environment());
    C --> D(database.session:create_tables());
    D --> E[api.main:app imported as FastAPI_App];
    E --> F(uvicorn.run(FastAPI_App));
```
