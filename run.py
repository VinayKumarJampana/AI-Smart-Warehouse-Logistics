import os
from app import create_app

# Create application instance using environment configuration
app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # Host on 127.0.0.1 and port 5000 in debug mode
    app.run(host="127.0.0.1", port=5000, debug=True)
