import copy
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, static_files={"/": "client/index.html", "/assets": "client/assets"})

estado = {"fase": "aguardando", "cacau": 96, "cacau_torrado": 0, "barras_comuns": 0, "barras_premium": 0}
jogadores = {}


def fato(causa, **extras):
    return {"estado": copy.deepcopy(estado), "causa": causa, **extras}


def jogadores_publicos():
    return {sid: copy.deepcopy(j) for sid, j in jogadores.items()}


@sio.event
async def connect(sid, environ, auth):
    auth = auth or {}
    papel = "mestre" if auth.get("papel") == "mestre" else "jogador"
    jogadores[sid] = {
        "nome": str(auth.get("nome") or "Anonimo")[:24],
        "papel": papel,
        "x": 145 if papel == "mestre" else 455,
        "y": 350 if papel == "mestre" else 325,
    }
    await sio.emit("estado.sincronizado", {**fato("conexao"), "meu_sid": sid, "jogadores": jogadores_publicos()}, to=sid)
    await sio.emit("jogador.entrou", {"causa": "conexao", "sid": sid, "jogador": copy.deepcopy(jogadores[sid])}, skip_sid=sid)


@sio.event
async def disconnect(sid):
    saiu = jogadores.pop(sid, None)
    if saiu:
        await sio.emit("jogador.saiu", {"causa": "desconexao", "sid": sid, "nome": saiu["nome"]})


@sio.on("jogador.movimentou")
async def movimentar(sid, dados=None):
    jogador = jogadores.get(sid)
    if not jogador or not dados:
        return
    try:
        x = max(28, min(932, float(dados.get("x", jogador["x"]))))
        y = max(68, min(510, float(dados.get("y", jogador["y"]))))
    except (TypeError, ValueError):
        return
    jogador["x"], jogador["y"] = x, y
    await sio.emit("jogador.posicao_atualizada", {"causa": "jogador.movimentou", "sid": sid, "x": x, "y": y}, skip_sid=sid)
