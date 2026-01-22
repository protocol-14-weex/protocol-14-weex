import os
import zipfile
import datetime

def make_bundle():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"weex_bot_vps_{timestamp}.zip"
    
    # Files/Dirs to include
    include_extensions = ['.py', '.txt', '.md', '.json', '.toml']
    include_files = ['Dockerfile', '.env.example']
    exclude_dirs = ['.git', '__pycache__', '.venv', '.gemini', 'tests', 'deploy']
    exclude_files = ['bot_decisions.log', 'bot_output_latest.log', 'output.txt', '.env'] # Don't send .env with secrets!
    
    print(f"📦 Creating bundle: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk directory
        for root, dirs, files in os.walk('.'):
            # Filtering dirs
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files:
                    continue
                    
                _, ext = os.path.splitext(file)
                if ext in include_extensions or file in include_files:
                    file_path = os.path.join(root, file)
                    # Archive name (relative path)
                    arcname = os.path.relpath(file_path, '.')
                    print(f"  + Adding {arcname}")
                    zipf.write(file_path, arcname)
                    
    print(f"\n✅ Bundle created! Transfer '{zip_filename}' to your VPS.")
    print(f"⚠️ NOTE: your local .env file was NOT included for security.")
    print(f"   You will need to create the .env file on the VPS manually.")

if __name__ == "__main__":
    make_bundle()
