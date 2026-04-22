from fastapi import APIRouter, HTTPException
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

router = APIRouter(prefix="/api/github", tags=["github"])

GITHUB_GRAPHQL = "https://api.github.com/graphql"
GITHUB_REST = "https://api.github.com"

CONTRIBUTIONS_QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
          date
          contributionCount
          weekday
          }
        }
      }
    }
    repositories(first: 6, orderBy: {field: STARGAZERS, direction: DESC}, privacy: PUBLIC) {
      nodes {
        name
        description
        url
        stargazerCount
        forkCount
        primaryLanguage {
          name
          color
        }
      }
    }
  }
}
"""


@router.get("/contributions/{username}")
async def get_contributions(username: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            GITHUB_GRAPHQL,
            json={"query": CONTRIBUTIONS_QUERY, "variables": {"username": username}},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Verintel/1.0",
                "Authorization": f"bearer {GITHUB_TOKEN}",
            }
        )

        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not reach GitHub API")
        
        data = r.json()
        print(f"DEBUG github response: {data}")

        if "errors" in data:
            raise HTTPException(status_code=404, detail="GitHub user not found")
        
        user = data.get("data", {}).get("user")
        if not user:
            raise HTTPException(status_code=404, detail="GitHub user not found")
        
        calendar = user["contributionsCollection"]["contributionCalendar"]
        repos = user["repositories"]["nodes"]

        return {
            "total_contributions": calendar["totalContributions"],
            "weeks": calendar["weeks"],
            "top_repos": repos,
        }