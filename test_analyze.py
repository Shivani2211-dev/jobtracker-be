import asyncio
from app.services.ai_service import analyze_resume_fit

async def test():
    result = await analyze_resume_fit("Test job description", "Test resume")
    print(f"Result: {result}")
    print(f"Type: {type(result)}")

asyncio.run(test())
