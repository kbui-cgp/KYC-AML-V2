from app import initialize_app

# Create app instance for gunicorn
app = initialize_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
