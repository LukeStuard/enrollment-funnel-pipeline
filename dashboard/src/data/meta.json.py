# When this build pulled its data (UTC), shown on every page.
import json
import sys
from datetime import datetime, timezone

json.dump({"built_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}, sys.stdout)
