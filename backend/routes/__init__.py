try:
    from backend.routes.auth import auth_bp
    from backend.routes.apis import apis_bp
    from backend.routes.frontend import frontend_bp
except ImportError:
    from routes.auth import auth_bp
    from routes.apis import apis_bp
    from routes.frontend import frontend_bp
