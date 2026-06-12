from fastapi import FastAPI
from routers import clients, auth, invoices

app = FastAPI()
app.include_router(clients.router)
app.include_router(auth.router)
app.include_router(invoices.router)

@app.get('/')
def info():

    return {"msg": {
        "API": "Facturo",
        "Version": "0.2",
        "Running": "run"
    }, "status": "ok"}