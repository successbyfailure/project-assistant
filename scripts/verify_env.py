import sys
import os

# Add the project root to sys.path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from config.coder import settings
    
    print("🔍 Verifying Project Assistant Environment...")
    
    is_coder = settings.is_coder_workspace
    print(f"🏠 Is Coder Workspace: {is_coder}")
    
    projects = settings.get_available_projects()
    print(f"📁 Projects Root: {settings.projects_root}")
    print(f"📂 Available Projects ({len(projects)}): {', '.join(projects) if projects else 'None'}")
    
    gh_auth = settings.verify_gh_auth()
    print(f"🔐 GitHub Authenticated: {gh_auth}")
    
    if is_coder and gh_auth and projects:
        print("\n✅ Environment verification PASSED!")
    else:
        print("\n⚠️ Environment verification incomplete (some checks failed).")

except ImportError as e:
    print(f"❌ Failed to import configuration: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error during verification: {e}")
    sys.exit(1)
