from dataclasses import dataclass
import os
PROXY_URI = os.getenv("PROXY","http://127.0.0.1:2080")

class BaseConfig:
    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                attr = getattr(self, k)
                if isinstance(v, dict):
                    assert attr is None or isinstance(attr, (BaseConfig, dict)), \
                        f"Expected {k} to be a dict, BaseConfig or None, got {type(attr)}"
                    attr.update(**v)
                else:
                    setattr(self, k, v)
            else:
                raise AttributeError(f"Invalid attribute {k}")


# api metrics taken from commandline on startup
@dataclass
class Api_Metrics(BaseConfig):
    host: str = '0.0.0.0'
    port: int = 5526
    num_workers: int = 4
    version: str = 'v2'
    loglevel:str = "info"
