"""
TrainSMART Backend — entry point.

Run in development:
    uvicorn app.main:app --reload

Or via this file:
    python main.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )