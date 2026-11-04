# Cacau Dourado — Vila da Chocolateria

Trabalho 01 de Linguagem de Programação e Paradigmas — Programação Orientada a Eventos — 2026/2.

**Desenvolvedor:** Jonathan Wiessner

## Estado atual — Etapa 6

A vila já funciona como jogo 2D cooperativo em tempo real. O jogador controla um chocolatier pelo mapa, produz chocolate em estações físicas, preserva o ponto do lote, atende clientes e agora também pode expandir a vila por construções com trabalhadores compartilhados.

### Controles
- `WASD` ou setas: mover
- `Shift`: correr
- `E`: interagir com a estação/lote próximo

## Novidades da Etapa 6

- três lotes físicos de expansão no mapa;
- `construcao.solicitada` do Jogador para o servidor;
- `construcao.iniciada` para todos quando o pedido é aceito;
- custo de 45 cacaus por expansão;
- limite de 2 chocolateiros ocupados simultaneamente;
- obra dura 9 segundos por temporizador do servidor;
- `construcao.concluida` libera o trabalhador e transforma o canteiro em anexo;
- cada expansão aumenta em +3 a produção automática de cacau;
- disputa segura pelo último trabalhador: somente um pedido vence;
- `operacao.recusada` vai apenas para quem fez o pedido;
- Mestre encerra a temporada na Prefeitura com `E`;
- `vila.encerrada` para todos e novas ações passam a ser recusadas;
- painel de eventos mostra `emit/on`, causa, dados e reação;
- contadores por evento aparecem no alto do painel;
- nome do desenvolvedor visível na aplicação.



## Teste rápido

1. Abra uma aba como Mestre e outra como Jogador.
2. Mestre vai até a Prefeitura e pressiona `E` para abrir a temporada.
3. Jogador vai até um lote `🏗` e pressiona `E`.
4. O lote vira canteiro, consome 45 cacaus e ocupa 1 chocolateiro.
5. Após 9 segundos o anexo aparece, o trabalhador é liberado e a produção sobe +3.
6. Para testar disputa, use Mestre + Jogador A + Jogador B conforme `GUIA_ETAPA_06.md`.
7. Mestre volta à Prefeitura e pressiona `E` para encerrar a temporada.

## Eventos mínimos

- `vila.iniciada`
- `construcao.solicitada`
- `construcao.iniciada`
- `operacao.recusada`
- `recurso.produzido`
- `construcao.concluida`
- `vila.encerrada`

Além deles, o jogo possui eventos próprios para movimento multiplayer, torrefação, moagem, perda do ponto, moldagem, vitrine e pedidos de clientes.

## Uso de IA

Foi utilizada IA como apoio na organização do projeto, implementação de partes da interface, revisão da lógica orientada a eventos e correção de erros. O projeto foi adaptado ao tema Vila de Chocolateria e testado em etapas. O desenvolvedor deve compreender e conseguir explicar os eventos, validações e mudanças de estado utilizados no trabalho.

