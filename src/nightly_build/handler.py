from git import Repo, Git
import shutil
from datetime import datetime
repo = "ipac"

def handler(event, context):
    Git("/tmp/").clone(f"codecommit::us-east-1://{repo}", branch="development", depth=1)
    try:
        repo_obj = Repo(f"/tmp/{repo}")
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%Y%m%d%H%M%S")
        repo_obj.create_tag(f"nightly_{timestampStr}Z")
        repo_obj.remotes.origin.push(f"nightly_{timestampStr}Z")
    finally:
        shutil.rmtree(f"/tmp/{repo}")
    return
if __name__ == "__main__":
    repo = "testrepo"
    handler(None, None)
