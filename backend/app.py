"""Compatibility entry point for Uvicorn and existing tests."""
from shop_api.main import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5600, reload=True)
