import copy
import math
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(
    sio,
    static_files={"/": "client/index.html", "/assets": "client/assets"},
)

# Coordenadas das estacoes no mundo 2D. O servidor usa as mesmas posicoes
# do Phaser para validar se o jogador realmente chegou ate a estacao.
ESTACOES = {
    "prefeitura": (165, 525),
    "torrefacao": (325, 185),
    "moagem": (590, 175),
    "moldagem": (840, 190),
    "vitrine": (1010, 500),
}
RAIO_INTERACAO = 92

estado = {
    "fase": "aguardando",
    "cacau": 96,
    "cacau_torrado": 0,
    "massa_cacau": 0,
    "barras": 0,
    "vitrine_barras": 0,
    "producao": 10,
    "intervalo": 6,
}

jogadores = {}


def fato(causa, **extras):
    """Todo fato enviado pelo servidor carrega o estado e a sua causa."""
    return {"estado": copy.deepcopy(estado), "causa": causa, **extras}


def jogadores_publicos():
    return {sid: copy.deepcopy(jogador) for sid, jogador in jogadores.items()}


def perto(sid, estacao):
    jogador = jogadores.get(sid)
    if not jogador:
        return False
    x, y = ESTACOES[estacao]
    return math.hypot(jogador["x"] - x, jogador["y"] - y) <= RAIO_INTERACAO


async def recusar(sid, motivo, causa):
    # Recusa e enviada somente ao cliente que fez o pedido.
    await sio.emit(
        "operacao.recusada",
        {"motivo": motivo, "causa": causa, "estado": copy.deepcopy(estado)},
        to=sid,
    )


@sio.event
async def connect(sid, environ, auth):
    auth = auth or {}
    papel = "mestre" if auth.get("papel") == "mestre" else "jogador"
    jogadores[sid] = {
        "nome": str(auth.get("nome") or "Anonimo")[:24],
        "papel": papel,
        "x": 185 if papel == "mestre" else 520,
        "y": 470 if papel == "mestre" else 515,
    }

    # Somente quem acabou de entrar precisa receber o estado inteiro.
    await sio.emit(
        "estado.sincronizado",
        {
            **fato("conexao"),
            "meu_sid": sid,
            "jogadores": jogadores_publicos(),
        },
        to=sid,
    )

    # Os outros clientes apenas desenham o novo personagem.
    await sio.emit(
        "jogador.entrou",
        {"causa": "conexao", "sid": sid, "jogador": copy.deepcopy(jogadores[sid])},
        skip_sid=sid,
    )


@sio.event
async def disconnect(sid):
    saiu = jogadores.pop(sid, None)
    if saiu:
        await sio.emit(
            "jogador.saiu",
            {"causa": "desconexao", "sid": sid, "nome": saiu["nome"]},
        )


@sio.on("jogador.movimentou")
async def movimentar(sid, dados=None):
    jogador = jogadores.get(sid)
    if not jogador or not dados:
        return

    try:
        x = max(30, min(1150, float(dados.get("x", jogador["x"]))))
        y = max(75, min(635, float(dados.get("y", jogador["y"]))))
    except (TypeError, ValueError):
        return

    jogador["x"], jogador["y"] = x, y
    await sio.emit(
        "jogador.posicao_atualizada",
        {"causa": "jogador.movimentou", "sid": sid, "x": x, "y": y},
        skip_sid=sid,
    )


@sio.on("vila.abertura_solicitada")
async def abrir_vila(sid, dados=None):
    pedido = "vila.abertura_solicitada"
    jogador = jogadores.get(sid)

    if not jogador or jogador["papel"] != "mestre":
        await recusar(sid, "Somente o Mestre pode abrir a temporada", pedido)
        return
    if not perto(sid, "prefeitura"):
        await recusar(sid, "Chegue perto da Prefeitura e pressione E", pedido)
        return
    if estado["fase"] != "aguardando":
        await recusar(sid, "A temporada ja foi aberta", pedido)
        return

    estado["fase"] = "aberta"
    sio.start_background_task(producao_cacau)
    await sio.emit("vila.iniciada", fato(pedido, por=jogador["nome"]))


async def producao_cacau():
    """Temporizador do servidor: produz cacau sem clique do jogador."""
    while estado["fase"] == "aberta":
        await sio.sleep(estado["intervalo"])
        if estado["fase"] != "aberta":
            break
        estado["cacau"] += estado["producao"]
        await sio.emit(
            "recurso.produzido",
            fato("temporizador", quantidade=estado["producao"]),
        )


@sio.on("lote.torrefacao_solicitada")
async def torrar(sid, dados=None):
    pedido = "lote.torrefacao_solicitada"
    jogador = jogadores.get(sid)

    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores produzem chocolate", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "torrefacao"):
        await recusar(sid, "Aproxime-se da Torrefacao", pedido)
        return
    if estado["cacau"] < 12:
        await recusar(sid, "Cacau insuficiente: sao necessarias 12 unidades", pedido)
        return

    estado["cacau"] -= 12
    estado["cacau_torrado"] += 10
    await sio.emit("lote.torrado", fato(pedido, por=jogador["nome"], gerado=10))


@sio.on("lote.moagem_solicitada")
async def moer(sid, dados=None):
    pedido = "lote.moagem_solicitada"
    jogador = jogadores.get(sid)

    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores produzem chocolate", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "moagem"):
        await recusar(sid, "Aproxime-se da Moagem", pedido)
        return
    if estado["massa_cacau"]:
        await recusar(sid, "Ja existe massa aguardando moldagem", pedido)
        return
    if estado["cacau_torrado"] < 10:
        await recusar(sid, "Primeiro torre um lote de cacau", pedido)
        return

    estado["cacau_torrado"] -= 10
    estado["massa_cacau"] = 1
    await sio.emit("lote.moido", fato(pedido, por=jogador["nome"]))


@sio.on("lote.moldagem_solicitada")
async def moldar(sid, dados=None):
    pedido = "lote.moldagem_solicitada"
    jogador = jogadores.get(sid)

    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores produzem chocolate", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "moldagem"):
        await recusar(sid, "Aproxime-se da Moldagem", pedido)
        return
    if not estado["massa_cacau"]:
        await recusar(sid, "Nao existe massa pronta para moldar", pedido)
        return

    estado["massa_cacau"] = 0
    estado["barras"] += 6
    await sio.emit(
        "lote.moldado",
        fato(pedido, por=jogador["nome"], quantidade=6),
    )


@sio.on("lote.vitrine_solicitada")
async def colocar_na_vitrine(sid, dados=None):
    pedido = "lote.vitrine_solicitada"
    jogador = jogadores.get(sid)

    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores abastecem a vitrine", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "vitrine"):
        await recusar(sid, "Aproxime-se da Vitrine", pedido)
        return
    if estado["barras"] <= 0:
        await recusar(sid, "Nao ha barras prontas para expor", pedido)
        return

    quantidade = estado["barras"]
    estado["barras"] = 0
    estado["vitrine_barras"] += quantidade
    await sio.emit(
        "lote.exposto",
        fato(pedido, por=jogador["nome"], quantidade=quantidade),
    )
