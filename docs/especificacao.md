# Especificação — Cacau Dourado: Vila da Chocolateria

**Integrante:** Jonathan Wiessner  
**Tipo de vila (sorteio):** Chocolataria  
**Fluxo do sorteio:** cacau → chocolate; torrefação, moagem e vitrine; o lote perde o ponto se não for moldado a tempo.


## 1. Ideia do jogo

A vila possui uma pequena cadeia artesanal de chocolate. O Jogador controla um personagem 2D pelo mapa e precisa se deslocar fisicamente entre as estações. O Mestre também possui personagem e controla o início e o fim da temporada.

Fluxo principal:

`cacau → torrefação → moagem → moldagem → barras de chocolate → vitrine → cliente`

A moagem cria um lote de massa com prazo de 14 segundos. Se o Jogador chegar à Moldagem dentro do prazo, produz chocolate premium. Se demorar, o evento `lote.perdeu_ponto` ocorre e o lote rende menos barras comuns.

## 2. Regras da vila

- Estoque inicial: 96 unidades de cacau.
- Produção automática: +10 cacaus a cada 6 segundos, enquanto a temporada estiver aberta.
- Torrefação: 12 cacaus viram 10 unidades de cacau torrado.
- Moagem: 10 unidades de cacau torrado criam 1 lote de massa.
- Ponto do chocolate: 14 segundos após a moagem.
- Moldagem no ponto: 8 barras premium.
- Moldagem fora do ponto: 4 barras comuns.
- Construção/expansão: custa 45 cacaus e ocupa 1 chocolateiro por 9 segundos.
- Limite inicial: 2 chocolateiros ocupados ao mesmo tempo.
- Cada expansão concluída aumenta em 3 a produção automática de cacau.
- Clientes surgem automaticamente e possuem prazo para serem atendidos.
- Pedidos totalmente atendidos com barras premium dão bônus de moedas e reputação.
- Meta: ganhar 160 moedas no total e alcançar 7 pontos de reputação.
- Diferencial: um Cacau Dourado aparece por tempo limitado em pontos do mapa; coletá-lo rende cacau e reputação.

## 3. Papéis

### Mestre
- Anda pelo mapa.
- Na Prefeitura, abre a temporada.
- Durante a temporada, na Prefeitura pode contratar chocolateiros.
- Na Praça pode realizar o Festival do Chocolate.
- Na Prefeitura pode encerrar a temporada.

### Jogador
- Anda com WASD/setas.
- Usa `E` perto das estações.
- Opera Torrefação, Moagem, Moldagem e Vitrine.
- Pode iniciar uma expansão da chocolateria no terreno de obra.
- Pode coletar o Cacau Dourado.

## 4. Eventos

| Evento | Emite | Recebe | O que muda |
|---|---|---|---|
| `estado.sincronizado` | Servidor | Quem conectou | Entrega estado atual e jogadores conectados |
| `vila.abertura_solicitada` | Mestre | Servidor | Pedido; não altera estado sozinho |
| `vila.iniciada` | Servidor | Todos | Fase passa para aberta e temporizadores iniciam |
| `construcao.solicitada` | Jogador | Servidor | Pedido de expansão |
| `construcao.iniciada` | Servidor | Todos | Debita cacau, ocupa trabalhador e inicia obra |
| `operacao.recusada` | Servidor | Só quem pediu | Informa o motivo sem alterar o estado indevidamente |
| `recurso.produzido` | Servidor | Todos | Temporizador aumenta o cacau |
| `construcao.concluida` | Servidor | Todos | Libera trabalhador, soma construção e aumenta produção |
| `vila.encerramento_solicitado` | Mestre | Servidor | Pedido para encerrar |
| `vila.encerrada` | Servidor | Todos | Fase passa para encerrada |
| `jogador.movimentou` | Cliente | Servidor | Atualiza posição oficial do personagem |
| `jogador.posicao_atualizada` | Servidor | Outros clientes | Move o avatar remoto |
| `lote.torrefacao_solicitada` | Jogador | Servidor | Solicita uso da Torrefação |
| `lote.torrado` | Servidor | Todos | Cacau vira cacau torrado |
| `lote.moagem_solicitada` | Jogador | Servidor | Solicita moagem |
| `lote.moido` | Servidor | Todos | Cria o lote e inicia prazo do ponto |
| `lote.perdeu_ponto` | Servidor | Todos | Temporizador marca o lote como fora do ponto |
| `lote.moldagem_solicitada` | Jogador | Servidor | Solicita moldagem |
| `lote.moldado` | Servidor | Todos | Gera barras premium ou comuns |
| `pedido_cliente.gerado` | Servidor | Todos | Temporizador cria cliente e prazo |
| `pedido.entrega_solicitada` | Jogador | Servidor | Solicita entrega na Vitrine |
| `pedido.entregue` | Servidor | Todos | Consome barras, soma moedas e reputação |
| `pedido.expirado` | Servidor | Todos | Remove cliente e reduz reputação |
| `cacau_dourado.apareceu` | Servidor | Todos | Cria bônus temporário no mapa |
| `cacau_dourado.coleta_solicitada` | Jogador | Servidor | Solicita coleta |
| `cacau_dourado.coletado` | Servidor | Todos | Soma cacau e reputação |
| `festival.solicitado` | Mestre | Servidor | Solicita festival |
| `festival.realizado` | Servidor | Todos | Consome recursos, aumenta reputação e produção |
| `melhoria.solicitada` | Mestre | Servidor | Solicita contratação |
| `melhoria.realizada` | Servidor | Todos | Aumenta limite de chocolateiros |
| `meta.atingida` | Servidor | Todos | Marca a meta da temporada como concluída |

## 5. Cenários obrigatórios de teste

### Recusa
**Dado** que a temporada ainda está aguardando,  
**quando** um Jogador emite `construcao.solicitada`,  
**então** o servidor emite `operacao.recusada` somente para esse Jogador com o motivo “A temporada não está aberta”.

### Passagem do tempo
**Dado** que o Mestre abriu a temporada e o servidor emitiu `vila.iniciada`,  
**quando** passam 6 segundos,  
**então** o servidor aumenta o cacau e emite `recurso.produzido` para todos sem ninguém clicar.

### Disputa
**Dado** que há apenas um chocolateiro livre,  
**quando** Jogador A e Jogador B emitem `construcao.solicitada` quase ao mesmo tempo,  
**então** somente um recebe `construcao.iniciada` e o outro recebe `operacao.recusada` com “Sem chocolateiro livre”.

## 6. Cenário próprio — perda do ponto

**Dado** que um Jogador concluiu a moagem e o servidor emitiu `lote.moido`,  
**quando** passam 14 segundos sem moldagem,  
**então** o servidor emite `lote.perdeu_ponto`; se o lote for moldado depois disso, ele rende 4 barras comuns em vez de 8 premium.
