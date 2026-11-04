import copy
import math
import time
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(
    sio,
    static_files={"/": "client/index.html", "/assets": "client/assets"},
)

# Coordenadas usadas tanto para validar as interacoes quanto para desenhar a vila.
ESTACOES = {
    "prefeitura": (165, 525),
    "torrefacao": (325, 185),
    "moagem": (590, 175),
    "moldagem": (840, 190),
    "vitrine": (1010, 500),
    "praca": (590, 390),
    "lote1": (475, 500),
    "lote2": (735, 500),
    "lote3": (1090, 165),
}
LOTES = ("lote1", "lote2", "lote3")
RAIO_INTERACAO = 92

# Regras documentadas em docs/especificacao.md antes da implementacao.
CUSTO_CONSTRUCAO = 45
TEMPO_OBRA = 9
GANHO_PRODUCAO = 3
CUSTO_MELHORIA = 55
LIMITE_MAX_TRABALHADORES = 4
CUSTO_FESTIVAL = 45
BONUS_FESTIVAL_REPUTACAO = 2
BONUS_FESTIVAL_PRODUCAO = 2
META_MOEDAS = 160
META_REPUTACAO = 7
CACAU_DOURADO_BONUS = 18
CACAU_DOURADO_PRAZO = 11
PONTOS_CACAU_DOURADO = [
    (270, 350), (430, 315), (750, 325), (925, 350), (285, 535), (900, 535)
]


def novo_lote():
    return {"status": "livre", "por": None, "conclui_em": None}


estado = {
    "fase": "aguardando",
    "cacau": 96,
    "cacau_torrado": 0,
    "massa_cacau": 0,
    "barras_premium": 0,
    "barras_comuns": 0,
    "vitrine_premium": 0,
    "vitrine_comuns": 0,
    "moedas": 0,
    "moedas_ganhas": 0,
    "reputacao": 0,
    "meta_atingida": False,
    "producao": 10,
    "intervalo": 6,
    "lote_atual": None,
    "pedido_ativo": None,
    "pedidos_entregues": 0,
    "pedidos_perdidos": 0,
    # Estado das construcoes obrigatorias do trabalho.
    "trabalhadores": 0,
    "limite_trabalhadores": 2,
    "custo_construcao": CUSTO_CONSTRUCAO,
    "tempo_obra": TEMPO_OBRA,
    "em_obra": 0,
    "concluidas": 0,
    "expansoes": {lote: novo_lote() for lote in LOTES},
    "cacau_dourado": None,
}

jogadores = {}
contador_lote = 0
contador_pedido = 0
indice_pedido = 0
contador_cacau_dourado = 0
indice_cacau_dourado = 0

CATALOGO = [
    {"cliente": "Dona Clara", "produto": "Caixa de bombons", "quantidade": 6, "recompensa": 26},
    {"cliente": "Sr. Augusto", "produto": "Barras artesanais", "quantidade": 8, "recompensa": 34},
    {"cliente": "Chef Marina", "produto": "Chocolate para sobremesa", "quantidade": 10, "recompensa": 44},
]


def fato(causa, **extras):
    """Todo fato carrega o estado atual e a causa que o gerou."""
    return {"estado": copy.deepcopy(estado), "causa": causa, **extras}


def jogadores_publicos():
    return {sid: copy.deepcopy(j) for sid, j in jogadores.items()}


def perto(sid, estacao):
    jogador = jogadores.get(sid)
    if not jogador or estacao not in ESTACOES:
        return False
    x, y = ESTACOES[estacao]
    return math.hypot(jogador["x"] - x, jogador["y"] - y) <= RAIO_INTERACAO


def total_vitrine():
    return estado["vitrine_premium"] + estado["vitrine_comuns"]


async def verificar_meta(causa):
    """Emite a meta uma unica vez quando moedas ganhas e reputacao atingem o objetivo."""
    if estado["meta_atingida"]:
        return
    if estado["moedas_ganhas"] >= META_MOEDAS and estado["reputacao"] >= META_REPUTACAO:
        estado["meta_atingida"] = True
        await sio.emit(
            "meta.atingida",
            fato(causa, meta_moedas=META_MOEDAS, meta_reputacao=META_REPUTACAO),
        )


def perto_cacau_dourado(sid):
    jogador = jogadores.get(sid)
    bonus = estado.get("cacau_dourado")
    if not jogador or not bonus:
        return False
    return math.hypot(jogador["x"] - bonus["x"], jogador["y"] - bonus["y"]) <= 72


async def recusar(sid, motivo, causa):
    # Recusa e um FATO direcionado: somente quem fez o pedido deve recebe-lo.
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
    # estado.sincronizado vai somente ao cliente novo: os demais ja possuem o estado.
    await sio.emit(
        "estado.sincronizado",
        {**fato("conexao"), "meu_sid": sid, "jogadores": jogadores_publicos()},
        to=sid,
    )
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
    sio.start_background_task(gerar_pedidos)
    sio.start_background_task(gerar_cacau_dourado)
    # FATO para todos: a partir daqui temporizadores e acoes de jogo ficam liberados.
    await sio.emit("vila.iniciada", fato(pedido, por=jogador["nome"]))


@sio.on("vila.encerramento_solicitado")
async def encerrar_vila(sid, dados=None):
    pedido = "vila.encerramento_solicitado"
    jogador = jogadores.get(sid)
    if not jogador or jogador["papel"] != "mestre":
        await recusar(sid, "Somente o Mestre pode encerrar a temporada", pedido)
        return
    if not perto(sid, "prefeitura"):
        await recusar(sid, "Chegue perto da Prefeitura para encerrar", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return

    estado["fase"] = "encerrada"
    # Limpa atividades temporarias; novas acoes serao recusadas pelo servidor.
    estado["pedido_ativo"] = None
    estado["lote_atual"] = None
    estado["massa_cacau"] = 0
    estado["cacau_dourado"] = None
    await sio.emit("vila.encerrada", fato(pedido, por=jogador["nome"]))


@sio.on("melhoria.solicitada")
async def contratar_chocolateiro(sid, dados=None):
    pedido = "melhoria.solicitada"
    jogador = jogadores.get(sid)
    if not jogador or jogador["papel"] != "mestre":
        await recusar(sid, "Somente o Mestre pode contratar chocolateiros", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "prefeitura"):
        await recusar(sid, "Chegue perto da Prefeitura", pedido)
        return
    if estado["limite_trabalhadores"] >= LIMITE_MAX_TRABALHADORES:
        await recusar(sid, "A vila ja possui o limite maximo de chocolateiros", pedido)
        return
    if estado["moedas"] < CUSTO_MELHORIA:
        await recusar(sid, f"Sao necessarias {CUSTO_MELHORIA} moedas para contratar", pedido)
        return

    estado["moedas"] -= CUSTO_MELHORIA
    estado["limite_trabalhadores"] += 1
    # FATO para todos: o limite compartilhado de trabalhadores aumentou.
    await sio.emit(
        "melhoria.realizada",
        fato(pedido, por=jogador["nome"], custo=CUSTO_MELHORIA, novo_limite=estado["limite_trabalhadores"]),
    )


@sio.on("festival.solicitado")
async def realizar_festival(sid, dados=None):
    pedido = "festival.solicitado"
    jogador = jogadores.get(sid)
    if not jogador or jogador["papel"] != "mestre":
        await recusar(sid, "Somente o Mestre pode realizar o Festival", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "praca"):
        await recusar(sid, "Va ate a Praca Central para realizar o Festival", pedido)
        return
    if estado["moedas"] < CUSTO_FESTIVAL:
        await recusar(sid, f"O Festival custa {CUSTO_FESTIVAL} moedas", pedido)
        return

    estado["moedas"] -= CUSTO_FESTIVAL
    estado["reputacao"] += BONUS_FESTIVAL_REPUTACAO
    estado["producao"] += BONUS_FESTIVAL_PRODUCAO
    await sio.emit(
        "festival.realizado",
        fato(
            pedido,
            por=jogador["nome"],
            custo=CUSTO_FESTIVAL,
            reputacao=BONUS_FESTIVAL_REPUTACAO,
            ganho_producao=BONUS_FESTIVAL_PRODUCAO,
        ),
    )
    await verificar_meta("festival.realizado")


async def gerar_cacau_dourado():
    global contador_cacau_dourado, indice_cacau_dourado
    await sio.sleep(11)
    while estado["fase"] == "aberta":
        if estado.get("cacau_dourado") is None:
            contador_cacau_dourado += 1
            x, y = PONTOS_CACAU_DOURADO[indice_cacau_dourado % len(PONTOS_CACAU_DOURADO)]
            indice_cacau_dourado += 1
            expira = time.time() + CACAU_DOURADO_PRAZO
            bonus = {
                "id": contador_cacau_dourado,
                "x": x,
                "y": y,
                "expira_em": expira,
                "prazo": CACAU_DOURADO_PRAZO,
            }
            estado["cacau_dourado"] = bonus
            await sio.emit(
                "cacau_dourado.apareceu",
                fato("temporizador_cacau_dourado", cacau_dourado=copy.deepcopy(bonus)),
            )
            sio.start_background_task(expirar_cacau_dourado, bonus["id"], expira)
        await sio.sleep(18)


async def expirar_cacau_dourado(bonus_id, expira):
    await sio.sleep(max(0, expira - time.time()))
    bonus = estado.get("cacau_dourado")
    if estado["fase"] != "aberta" or not bonus or bonus.get("id") != bonus_id:
        return
    estado["cacau_dourado"] = None
    await sio.emit(
        "cacau_dourado.expirado",
        fato("temporizador_cacau_dourado", bonus_id=bonus_id),
    )


@sio.on("cacau_dourado.coleta_solicitada")
async def coletar_cacau_dourado(sid, dados=None):
    pedido = "cacau_dourado.coleta_solicitada"
    jogador = jogadores.get(sid)
    bonus = estado.get("cacau_dourado")
    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores coletam o Cacau Dourado", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not bonus:
        await recusar(sid, "O Cacau Dourado nao esta mais disponivel", pedido)
        return
    if not perto_cacau_dourado(sid):
        await recusar(sid, "Aproxime-se do Cacau Dourado", pedido)
        return

    coletado = copy.deepcopy(bonus)
    estado["cacau_dourado"] = None
    estado["cacau"] += CACAU_DOURADO_BONUS
    estado["reputacao"] += 1
    await sio.emit(
        "cacau_dourado.coletado",
        fato(pedido, por=jogador["nome"], bonus=CACAU_DOURADO_BONUS, cacau_dourado=coletado),
    )
    await verificar_meta("cacau_dourado.coletado")


async def producao_cacau():
    while estado["fase"] == "aberta":
        await sio.sleep(estado["intervalo"])
        if estado["fase"] != "aberta":
            break
        estado["cacau"] += estado["producao"]
        # Evento espontaneo do servidor: ninguem clicou para produzir.
        await sio.emit(
            "recurso.produzido",
            fato("temporizador_producao", quantidade=estado["producao"]),
        )


@sio.on("construcao.solicitada")
async def construir(sid, dados=None):
    pedido = "construcao.solicitada"
    jogador = jogadores.get(sid)
    dados = dados or {}
    lote_id = str(dados.get("lote") or "")

    # Toda validacao ocorre ANTES de alterar o estado e sem await entre validacao e alteracao.
    # Assim dois pedidos simultaneos disputando o ultimo chocolateiro sao decididos em sequencia.
    if not jogador or jogador["papel"] != "jogador":
        motivo = "Somente Jogadores podem iniciar expansoes"
    elif estado["fase"] != "aberta":
        motivo = "A temporada nao esta aberta"
    elif lote_id not in LOTES:
        motivo = "Lote de construcao invalido"
    elif not perto(sid, lote_id):
        motivo = "Aproxime-se do lote de expansao"
    elif estado["expansoes"][lote_id]["status"] != "livre":
        motivo = "Este lote ja esta ocupado"
    elif estado["trabalhadores"] >= estado["limite_trabalhadores"]:
        motivo = "Sem chocolateiro livre"
    elif estado["cacau"] < CUSTO_CONSTRUCAO:
        motivo = f"Cacau insuficiente: a expansao custa {CUSTO_CONSTRUCAO}"
    else:
        motivo = None

    if motivo:
        await recusar(sid, motivo, pedido)
        return

    # Secao critica: nenhuma espera entre conferir disponibilidade e ocupar o recurso.
    estado["cacau"] -= CUSTO_CONSTRUCAO
    estado["trabalhadores"] += 1
    estado["em_obra"] += 1
    conclui_em = time.time() + TEMPO_OBRA
    estado["expansoes"][lote_id] = {
        "status": "em_obra",
        "por": jogador["nome"],
        "conclui_em": conclui_em,
    }
    nome = jogador["nome"]

    # FATO para todos: transforma o lote em canteiro de obras.
    await sio.emit(
        "construcao.iniciada",
        fato(
            pedido,
            por=nome,
            lote=lote_id,
            custo=CUSTO_CONSTRUCAO,
            tempo=TEMPO_OBRA,
        ),
    )
    sio.start_background_task(concluir_obra, lote_id, nome, conclui_em)


async def concluir_obra(lote_id, nome, conclui_em):
    await sio.sleep(max(0, conclui_em - time.time()))
    lote = estado["expansoes"].get(lote_id)
    if not lote or lote.get("status") != "em_obra":
        return

    # A obra ja aceita termina por temporizador mesmo que o Mestre encerre logo depois.
    estado["trabalhadores"] = max(0, estado["trabalhadores"] - 1)
    estado["em_obra"] = max(0, estado["em_obra"] - 1)
    estado["concluidas"] += 1
    estado["producao"] += GANHO_PRODUCAO
    estado["expansoes"][lote_id] = {
        "status": "concluida",
        "por": nome,
        "conclui_em": None,
    }

    # FATO gerado pelo temporizador: libera trabalhador e melhora a vila.
    await sio.emit(
        "construcao.concluida",
        fato(
            "construcao.iniciada (temporizador)",
            por=nome,
            lote=lote_id,
            ganho_producao=GANHO_PRODUCAO,
        ),
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
    global contador_lote
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
    if estado["lote_atual"] is not None:
        await recusar(sid, "Ja existe um lote aguardando moldagem", pedido)
        return
    if estado["cacau_torrado"] < 10:
        await recusar(sid, "Primeiro torre um lote de cacau", pedido)
        return

    contador_lote += 1
    estado["cacau_torrado"] -= 10
    estado["massa_cacau"] = 1
    expira = time.time() + 14
    estado["lote_atual"] = {
        "id": contador_lote,
        "status": "no_ponto",
        "expira_em": expira,
        "prazo": 14,
        "por": jogador["nome"],
    }
    await sio.emit(
        "lote.moido",
        fato(pedido, por=jogador["nome"], lote=copy.deepcopy(estado["lote_atual"])),
    )
    sio.start_background_task(perder_ponto, contador_lote, expira)


async def perder_ponto(lote_id, expira):
    await sio.sleep(max(0, expira - time.time()))
    lote = estado.get("lote_atual")
    if (
        estado["fase"] != "aberta"
        or not lote
        or lote.get("id") != lote_id
        or lote.get("status") != "no_ponto"
    ):
        return
    lote["status"] = "fora_do_ponto"
    await sio.emit(
        "lote.perdeu_ponto",
        fato("temporizador_ponto", lote=copy.deepcopy(lote)),
    )


@sio.on("lote.moldagem_solicitada")
async def moldar(sid, dados=None):
    pedido = "lote.moldagem_solicitada"
    jogador = jogadores.get(sid)
    lote = estado.get("lote_atual")
    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores produzem chocolate", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido)
        return
    if not perto(sid, "moldagem"):
        await recusar(sid, "Aproxime-se da Moldagem", pedido)
        return
    if not lote:
        await recusar(sid, "Nao existe massa pronta para moldar", pedido)
        return

    premium = lote["status"] == "no_ponto"
    quantidade = 8 if premium else 4
    if premium:
        estado["barras_premium"] += quantidade
    else:
        estado["barras_comuns"] += quantidade
    estado["massa_cacau"] = 0
    estado["lote_atual"] = None
    await sio.emit(
        "lote.moldado",
        fato(
            pedido,
            por=jogador["nome"],
            qualidade="premium" if premium else "comum",
            quantidade=quantidade,
        ),
    )


@sio.on("lote.vitrine_solicitada")
async def abastecer_vitrine(sid, dados=None):
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
    if estado["barras_premium"] + estado["barras_comuns"] <= 0:
        await recusar(sid, "Nao ha barras prontas para expor", pedido)
        return

    premium = estado["barras_premium"]
    comuns = estado["barras_comuns"]
    estado["vitrine_premium"] += premium
    estado["vitrine_comuns"] += comuns
    estado["barras_premium"] = 0
    estado["barras_comuns"] = 0
    await sio.emit(
        "lote.exposto",
        fato(pedido, por=jogador["nome"], premium=premium, comuns=comuns),
    )


async def gerar_pedidos():
    global contador_pedido, indice_pedido
    await sio.sleep(7)
    while estado["fase"] == "aberta":
        if estado["pedido_ativo"] is None:
            base = CATALOGO[indice_pedido % len(CATALOGO)]
            indice_pedido += 1
            contador_pedido += 1
            expira = time.time() + 30
            pedido = {
                "id": contador_pedido,
                "cliente": base["cliente"],
                "produto": base["produto"],
                "quantidade": base["quantidade"],
                "recompensa": base["recompensa"],
                "bonus_premium": 12,
                "expira_em": expira,
                "prazo": 30,
            }
            estado["pedido_ativo"] = pedido
            await sio.emit(
                "pedido_cliente.gerado",
                fato("temporizador_clientes", pedido=copy.deepcopy(pedido)),
            )
            sio.start_background_task(expirar_pedido, pedido["id"], expira)
        await sio.sleep(10)


async def expirar_pedido(pedido_id, expira):
    await sio.sleep(max(0, expira - time.time()))
    pedido = estado.get("pedido_ativo")
    if estado["fase"] != "aberta" or not pedido or pedido.get("id") != pedido_id:
        return
    estado["pedido_ativo"] = None
    estado["pedidos_perdidos"] += 1
    estado["reputacao"] = max(0, estado["reputacao"] - 1)
    await sio.emit(
        "pedido.expirado",
        fato("temporizador_pedido", pedido_id=pedido_id),
    )


@sio.on("pedido.entrega_solicitada")
async def entregar_pedido(sid, dados=None):
    pedido_evento = "pedido.entrega_solicitada"
    jogador = jogadores.get(sid)
    pedido = estado.get("pedido_ativo")
    if not jogador or jogador["papel"] != "jogador":
        await recusar(sid, "Somente Jogadores entregam pedidos", pedido_evento)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada nao esta aberta", pedido_evento)
        return
    if not perto(sid, "vitrine"):
        await recusar(sid, "Va ate a Vitrine para atender o cliente", pedido_evento)
        return
    if not pedido:
        await recusar(sid, "Nao ha cliente aguardando", pedido_evento)
        return
    if total_vitrine() < pedido["quantidade"]:
        await recusar(
            sid,
            f"A vitrine tem {total_vitrine()} barras; o pedido precisa de {pedido['quantidade']}",
            pedido_evento,
        )
        return

    quantidade = pedido["quantidade"]
    premium_usadas = min(estado["vitrine_premium"], quantidade)
    comuns_usadas = quantidade - premium_usadas
    estado["vitrine_premium"] -= premium_usadas
    estado["vitrine_comuns"] -= comuns_usadas

    tudo_premium = premium_usadas == quantidade
    recompensa = pedido["recompensa"] + (pedido["bonus_premium"] if tudo_premium else 0)
    estado["moedas"] += recompensa
    estado["moedas_ganhas"] += recompensa
    estado["reputacao"] += 2 if tudo_premium else 1
    estado["pedidos_entregues"] += 1
    atendido = copy.deepcopy(pedido)
    estado["pedido_ativo"] = None

    await sio.emit(
        "pedido.entregue",
        fato(
            pedido_evento,
            por=jogador["nome"],
            pedido=atendido,
            premium=tudo_premium,
            recompensa_final=recompensa,
        ),
    )
    await verificar_meta("pedido.entregue")
