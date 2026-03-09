# Author: CTCC
# Description: Pydantic model for Primary BCR config (load_primary_bcr_config return type).

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict


class PrimaryBCRConfig(BaseModel):
    """
    Primary BCR configuration: module enable/disable flags by category.
    Returned by load_primary_bcr_config (yaml_loaders, json_loaders).
    """

    model_config = ConfigDict(extra="ignore")

    operational: Optional[Dict[str, bool]] = None
    risk: Optional[Dict[str, bool]] = None
    energy: Optional[Dict[str, bool]] = None
    benefits: Optional[Dict[str, bool]] = None
