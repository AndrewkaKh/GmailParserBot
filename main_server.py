from server import create_app
from server.routes import routes

app = create_app()
app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
