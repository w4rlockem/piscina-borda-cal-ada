# Piscina menor — troca de borda e calçada

Estudo para escolher o material de **borda e calçada** da piscina menor
(fibra, ~6 m) em Ponta da Fruta, Vila Velha — ES.

Dez materiais de piso e seis de borda, aplicados sobre as fotos reais do
local. As montagens não são renderização fotorrealista: são estudo de
acabamento. Comunicam cor, contraste e paginação; não simulam reflexo novo
nem recalculam sombra.

## O que abrir

| Arquivo | Para quê |
|---|---|
| `Piscina menor - materiais de borda e calcada (novo).pptx` | **26 slides, versão atual.** Para levar impresso ao marmorista |
| `deck/palestra.html` | Apresentação de tela cheia, para projetor. Setas navegam, `G` abre o mapa, `F` tela cheia |
| `deck/piscina-menor.html` | Página de leitura, rola no celular. Tem comparador interativo dos 10 materiais |
| `docs/superpowers/specs/` | O spec: diagnóstico, decisões, o que foi verificado e o que deu errado no caminho |

> O arquivo `...calcada.pptx` (sem "novo") é a versão anterior, de 18 slides,
> ainda sem a seção da borda. Pode apagar quando fechar o PowerPoint.

## Como regerar

As três entregas saem das mesmas imagens. Ordem obrigatória: `gerar.py`
primeiro, porque os outros consomem o que ele produz.

```bash
cd deck
python gerar.py          # ~3 min: monta as 50+ imagens em deck/render/
python build_pptx.py     # o PPTX
python build_palestra.py # a apresentação
python build_html.py     # a página de leitura
```

Dependências: `numpy`, `scipy`, `Pillow`, `python-pptx`.

## Para mudar um material

Edite [`deck/materiais.json`](deck/materiais.json) e rode os quatro
comandos acima. É o único arquivo que precisa de edição manual — os slides,
a tabela, o comparador e as três entregas se atualizam juntos, sem risco de
divergirem.

- `materiais` — os 10 de piso, com nota de 1 a 5 em cinco critérios
- `bordas` — os 6 de borda, com critérios próprios (numa borda o que decide
  é aderência molhada, resistência ao cloro e peça sob medida)

Nota 5 é sempre o melhor, inclusive em `custo`: 5 quer dizer mais barato.

## Como as montagens funcionam

A calçada é um plano. A piscina é um retângulo conhecido (6,0 × 3,0 m)
deitado nesse plano — achando seus quatro cantos sai a correspondência
entre plano e foto, e cada pixel vira uma coordenada em metros. A paginação
é desenhada em metros, então as juntas convergem no ponto de fuga certo e a
placa de 40 cm tem 40 cm.

A iluminação vem da própria foto: luminância desfocada dentro da máscara,
normalizada, multiplicando o material novo. Por isso a sombra da mangueira e
o brilho do sol atravessam a montagem.

Detalhes e os defeitos corrigidos no caminho estão no spec.

## Ressalvas que valem para tudo

- Medidas estimadas por foto: **60 a 75 m² de piso e ~18 m de borda**.
  Confirmar com trena.
- Preços são faixas indicativas para a Grande Vitória/ES, a confirmar com
  fornecedor local.
- Cor de pedra natural varia por lote. **Peça amostra física** e veja a placa
  sob o sol do local, molhada e seca, antes de fechar.
