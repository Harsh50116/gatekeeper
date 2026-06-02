from digest.web.app import app  # noqa

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    app.run(debug=True, port=port)
