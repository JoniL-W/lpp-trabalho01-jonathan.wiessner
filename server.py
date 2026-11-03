import copy
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, static_files={"/": "client/index.html", "/assets": "client/assets"})

estado = {
    "fase": "aguardando",
    "cacau": 96,
    "cacau_torrado": 0,
    "barras_comuns": 0,
    "barras_premium": 0,
}

jogadores = {}


def fato(causa, **extras):
    return {"estado": copy.deepcopy(estado), "causa": causa, **extras}


@sio.event
async def connect(sid, environ, auth):
    auth = auth or {}
    jogadores[sid] = {
        "nome": str(auth.get("nome") or "Anonimo")[:24],
        "papel": "mestre" if auth.get("papel") == "mestre" else "jogador",
    }
    # Primeiro fato do sistema: somente o cliente recém-conectado recebe o estado atual.
    await sio.emit("estado.sincronizado", fato("conexao", meu_sid=sid), to=sid)


@sio.event
async def disconnect(sid):
    jogadores.pop(sid, None)
