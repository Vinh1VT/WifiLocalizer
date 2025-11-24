# main.py
from fastapi import FastAPI
from database import create_db_and_tables
from routers import ttn,frontend,admin

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# C'est ici que la magie opère :
# On ajoute les routes du frontend (à la racine)
app.include_router(frontend.router)

# On ajoute les routes TTN (préfixées par /ttn pour être propre)
# L'URL finale sera donc : http://ton-domaine/ttn/webhook
app.include_router(ttn.router, prefix="/ttn", tags=["TTN"])

app.include_router(admin.router, prefix="/admin", tags=["Admin"])
