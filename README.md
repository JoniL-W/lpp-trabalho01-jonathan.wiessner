# Cacau Dourado — Vila da Chocolateria

Trabalho 01 — Linguagem de Programação e Paradigmas — Programação Orientada a Eventos — 2026/2.

**Desenvolvedor:** Jonathan Wiessner  
**GitHub:** @JoniL-W  
**Tema sorteado:** Vila de Chocolateria

## 1. Visão geral

O **Cacau Dourado** é um jogo 2D cooperativo em tempo real. Vários clientes acessam a mesma vila e compartilham o mesmo estado mantido pelo servidor. O jogador controla um chocolatier no mapa, se desloca fisicamente até as estações e usa eventos para produzir chocolate, atender clientes e expandir a vila. O Mestre abre e encerra a temporada, pode contratar chocolateiros e realizar o Festival do Chocolate.

O foco do trabalho é **Programação Orientada a Eventos**: o cliente emite pedidos, o servidor valida e decide o que acontece, e os clientes escutam fatos e reagem visualmente sem recarregar a página.

## 2. Tecnologias

- **Servidor:** Python 3 + `python-socketio` + `uvicorn`
- **Comunicação em tempo real:** Socket.IO
- **Interface/HUD:** Vue 3 por CDN
- **Jogo 2D:** Phaser 3 + Arcade Physics por CDN
- **Estado:** memória do servidor, sem banco de dados

A arte principal da vila, personagens, prédios, efeitos e objetos é desenhada programaticamente no Phaser. Não foram utilizados assets copiados de jogos comerciais.

## 3. Controles

| Tecla | Ação |
|---|---|
| `WASD` ou setas | mover o personagem |
| `Shift` | correr |
| `E` | interagir com estação, lote, Cacau Dourado ou ação contextual |
| `Q` | Mestre encerra a temporada quando está próximo da Prefeitura |

## 4. Papéis

### Mestre

- anda pelo mapa;
- abre a temporada na Prefeitura com `E`;
- durante a temporada, contrata chocolateiros na Prefeitura com `E`;
- realiza o Festival do Chocolate na Praça com `E`;
- encerra a temporada na Prefeitura com `Q`.

### Jogador

- anda pelo mapa;
- opera Torrefação, Moagem, Moldagem e Vitrine;
- inicia expansões nos lotes disponíveis;
- atende pedidos de clientes;
- coleta o Cacau Dourado quando ele aparece.

## 5. Fluxo principal do jogo

```text
Cacau
  ↓
Torrefação
  ↓
Moagem
  ↓
14 segundos para preservar o ponto
  ↓
Moldagem
  ↓
Chocolate Premium ou Comum
  ↓
Vitrine
  ↓
Cliente
  ↓
Moedas + Reputação
```

### Regras principais

- estoque inicial: **96 cacaus**;
- produção automática: **+10 cacaus a cada 6 segundos**;
- torrefação: **12 cacaus → 10 torrados**;
- moagem: **10 torrados → 1 lote**;
- prazo do ponto: **14 segundos**;
- moldagem no ponto: **8 barras premium**;
- moldagem fora do ponto: **4 barras comuns**;
- expansão: **45 cacaus**, **9 segundos**, ocupa 1 chocolateiro;
- limite inicial: **2 chocolateiros**;
- cada expansão concluída: **+3 de produção automática**;
- contratação: **55 moedas**, aumenta o limite de chocolateiros até 4;
- Festival do Chocolate: **45 moedas**, **+2 reputação** e **+2 produção**;
- Cacau Dourado: aparece por tempo limitado, rende **+18 cacaus** e **+1 reputação**;
- meta da temporada: **160 moedas ganhas no total + 7 de reputação**.

## 6. Instalação

No Windows, abra o terminal dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A pasta `.venv` não deve ser enviada para o GitHub.

## 7. Executar

```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --reload
```

Abra no navegador:

```text
http://localhost:8000
```


## 8. Como testar com duas abas

1. Abra duas abas em `http://localhost:8000`.
2. Na primeira, entre como **Mestre**.
3. Na segunda, entre como **Jogador**.
4. Observe que os dois personagens aparecem na mesma vila.
5. Mova um personagem e confira o movimento na outra aba.
6. O Mestre vai até a Prefeitura e pressiona `E` para abrir a temporada.
7. O Jogador segue a rota Torrefação → Moagem → Moldagem → Vitrine.
8. Após a Moagem, teste uma vez chegando à Moldagem dentro de 14 segundos e outra deixando o prazo acabar.
9. Aguarde um cliente e entregue o pedido na Vitrine.
10. Aguarde o Cacau Dourado, corra até ele e pressione `E`.
11. Inicie uma expansão em um lote e aguarde a conclusão automática da obra.
12. O Mestre pode gastar moedas para contratar chocolateiros ou fazer o Festival na Praça.
13. Ao final, o Mestre volta à Prefeitura e pressiona `Q` para encerrar a temporada.

## 9. Como testar recusa e disputa

### Recusa

1. Reinicie o servidor.
2. Entre apenas como Jogador.
3. Antes de o Mestre abrir a temporada, vá até um lote e pressione `E`.
4. Somente esse cliente deve receber `operacao.recusada` com o motivo de que a temporada não está aberta.

### Disputa pelo último chocolateiro

Use três abas: **Mestre**, **Jogador A** e **Jogador B**.

1. Mestre abre a temporada.
2. Jogador A inicia uma obra no Lote 1; fica 1/2 chocolateiros ocupados.
3. Antes da obra terminar, Jogador A vai ao Lote 2 e Jogador B ao Lote 3.
4. Os dois pressionam `E` quase ao mesmo tempo.
5. Somente um pedido deve gerar `construcao.iniciada`.
6. O outro recebe `operacao.recusada` com “Sem chocolateiro livre”.
7. O estado nunca ultrapassa o limite de trabalhadores.

## 10. Painel de eventos

O painel exibe em tempo real os eventos didáticos e de gameplay com:

- `emit` ou `on`;
- nome do evento;
- horário;
- causa;
- dados relevantes;
- reação executada pelo cliente;
- contador de ocorrências por evento.

Os eventos de posição do personagem são telemetria de alta frequência. Eles continuam usando Socket.IO e atualizando os outros clientes, mas não são adicionados linha por linha ao histórico detalhado para não esconder os eventos didáticos do trabalho.

## 11. Eventos do sistema

### Conexão e multiplayer

- `estado.sincronizado` — servidor → cliente recém-conectado
- `jogador.entrou` — servidor → outros clientes
- `jogador.saiu` — servidor → todos
- `jogador.movimentou` — cliente → servidor
- `jogador.posicao_atualizada` — servidor → outros clientes

### Temporada

- `vila.abertura_solicitada` — Mestre → servidor
- `vila.iniciada` — servidor → todos
- `vila.encerramento_solicitado` — Mestre → servidor
- `vila.encerrada` — servidor → todos

### Construção

- `construcao.solicitada` — Jogador → servidor
- `construcao.iniciada` — servidor → todos
- `construcao.concluida` — servidor → todos, por temporizador
- `operacao.recusada` — servidor → somente quem fez o pedido

### Produção de chocolate

- `lote.torrefacao_solicitada` — Jogador → servidor
- `lote.torrado` — servidor → todos
- `lote.moagem_solicitada` — Jogador → servidor
- `lote.moido` — servidor → todos
- `lote.perdeu_ponto` — servidor → todos, por temporizador
- `lote.moldagem_solicitada` — Jogador → servidor
- `lote.moldado` — servidor → todos
- `lote.vitrine_solicitada` — Jogador → servidor
- `lote.exposto` — servidor → todos
- `recurso.produzido` — servidor → todos, por temporizador

### Clientes

- `pedido_cliente.gerado` — servidor → todos, por temporizador
- `pedido.entrega_solicitada` — Jogador → servidor
- `pedido.entregue` — servidor → todos
- `pedido.expirado` — servidor → todos, por temporizador

### Diferenciais

- `cacau_dourado.apareceu` — servidor → todos
- `cacau_dourado.coleta_solicitada` — Jogador → servidor
- `cacau_dourado.coletado` — servidor → todos
- `cacau_dourado.expirado` — servidor → todos
- `melhoria.solicitada` — Mestre → servidor
- `melhoria.realizada` — servidor → todos
- `festival.solicitado` — Mestre → servidor
- `festival.realizado` — servidor → todos
- `meta.atingida` — servidor → todos

## 12. Perguntas

### 1. Quais eventos o seu sistema emite e escuta?

O cliente emite **pedidos**, como `vila.abertura_solicitada`, `construcao.solicitada`, `lote.torrefacao_solicitada`, `pedido.entrega_solicitada`, `festival.solicitado` e `cacau_dourado.coleta_solicitada`. O servidor escuta esses pedidos, valida o estado e emite **fatos**, como `vila.iniciada`, `construcao.iniciada`, `recurso.produzido`, `lote.moldado`, `pedido.entregue`, `festival.realizado` e `meta.atingida`. Os clientes escutam esses fatos e atualizam o Phaser e o HUD.

### 2. Como o sistema sabe quando deve atualizar os outros jogadores?

O servidor é a fonte da verdade. Quando um pedido é aceito ou um temporizador gera uma mudança, o servidor altera o estado e usa `sio.emit(...)` para emitir um fato. Os clientes conectados possuem handlers registrados com `socket.on(...)` por meio da função `ouvir(...)`. Quando o fato chega, o cliente copia o novo estado e atualiza automaticamente a interface e o cenário. Por isso nenhum jogador precisa recarregar a página.

### 3. Que parte do código mostra claramente o uso do paradigma orientado a eventos?

No `client/index.html`, as funções `pedir(...)` e `ouvir(...)` deixam a separação explícita: `pedir(...)` registra e emite pedidos do cliente, enquanto `ouvir(...)` registra fatos recebidos e executa a reação visual correspondente. No `server.py`, os handlers `@sio.on(...)` recebem os pedidos e decidem o que acontece. Além disso, `producao_cacau()`, `concluir_obra()`, `perder_ponto()`, `gerar_pedidos()` e `gerar_cacau_dourado()` mostram temporizadores do servidor produzindo eventos sem clique do usuário.

## 13. Estrutura do projeto

```text
lpp-trabalho01-jonathan/
├── client/
│   ├── index.html
│   └── assets/
├── docs/
│   └── especificacao.md
├── server.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 14. Histórico de desenvolvimento sugerido

O projeto foi construído de forma incremental:

1. `docs: especificacao da vila de chocolateria`
2. `feat: estrutura inicial e sincronizacao em tempo real`
3. `feat: personagem controlavel e movimento multiplayer`
4. `feat: mapa expandido e cadeia interativa da chocolateria`
5. `feat: ponto do chocolate e pedidos com prazo`
6. `refactor: melhorias na interface e pedidos com prazos e clientes`
7. `feat: construcoes e disputas`
8. `feat: finalizar diferenciais documentacao e testes`

## 15. Uso de Inteligência Artificial

Foi utilizada Inteligência Artificial como ferramenta de apoio durante o desenvolvimento. O apoio incluiu organização das etapas, sugestões para a interface 2D, revisão de código, criação e revisão de eventos, identificação de erros e apoio na documentação.

O projeto foi adaptado, executado e testado durante o desenvolvimento. O desenvolvedor compreende e deve ser capaz de explicar os eventos, as validações no servidor, os temporizadores, as mudanças de estado e a comunicação entre os clientes.

## 16. Observações finais

- o servidor é sempre a fonte da verdade;
- o cliente nunca deve debitar recursos ou concluir uma ação compartilhada sozinho;
- todas as validações importantes são feitas no servidor;
- a recusa é enviada somente para quem fez o pedido;
- produção, obras, perda do ponto, clientes e Cacau Dourado utilizam temporizadores do servidor;
- o estado é mantido apenas em memória, conforme permitido no trabalho;
- o jogo foi projetado para funcionar com várias abas abertas simultaneamente.
