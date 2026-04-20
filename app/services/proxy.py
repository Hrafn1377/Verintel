import itertools
from dataclasses import dataclass


@dataclass
class Proxy:
    host: str
    port: int
    username: str | None = None
    password: str | None = None

    def to_url(self) -> str:
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"
    
    def to_playwright(self) -> dict:
        proxy = {"server": f"http://{self.host}:{self.port}"}
        if self.username and self.password:
            proxy["username"] = self.username
            proxy["password"] = self.password
        return proxy
    

PROXIES: list[Proxy] = [
    # add your proxies here when you have them
    # Proxy(host="proxy1.example.com", port=8080, username="user", password="pass"),
]

_pool = intertools.cycle(PROXIES) if PROXIES else None


def get_proxy() -> Proxy | None:
    if _pool is None:
        return None
    return next(_pool)


def has_proxies() -> bool:
    return bool(PROXIES)