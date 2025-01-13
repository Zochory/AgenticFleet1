import os
import subprocess

def main():
    """Run the Chainlit application."""
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "app", "app.py")
    subprocess.run(["chainlit", "run", app_path, "--port", "8001"], check=True)

if __name__ == "__main__":
    main()