"""Allow ``python -m forge`` to invoke the CLI."""
from forge.core import main

raise SystemExit(main())
