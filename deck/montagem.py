"""Aplica materiais sobre as fotos reais da piscina.

Ideia central: a calcada e um plano. Conhecendo a homografia entre esse
plano e a foto, cada pixel vira uma coordenada em metros. A paginacao das
placas e entao desenhada em metros e a perspectiva sai de graca -- as
juntas convergem no ponto de fuga certo e a placa de 40 cm tem 40 cm.

A iluminacao vem da propria foto: o campo de luz e extraido por desfoque
(que remove a textura antiga e preserva as sombras) e multiplica o material
novo. Por isso a sombra da mangueira e o brilho do sol atravessam a
montagem.
"""
import json
import os
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull
from itertools import combinations

# Ancorado no arquivo, nao no diretorio de execucao: os scripts rodam tanto
# da raiz do projeto quanto de dentro de deck/.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def caminho(rel):
    return os.path.join(RAIZ, rel)


LARG, ALT = 1600, 1200

# ---------------------------------------------------------------- geometria


def homografia(origem, destino):
    A = []
    for (x, y), (u, v) in zip(origem, destino):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, Vt = np.linalg.svd(np.array(A))
    return (Vt[-1] / Vt[-1, -1]).reshape(3, 3)


def coords_mundo(Hinv):
    """Para cada pixel da foto, sua coordenada (u, v) em metros no plano."""
    ys, xs = np.mgrid[0:ALT, 0:LARG]
    p = np.stack([xs, ys, np.ones_like(xs)], axis=-1).astype(float)
    q = p @ Hinv.T
    w = np.where(np.abs(q[..., 2]) < 1e-9, 1e-9, q[..., 2])
    return q[..., 0] / w, q[..., 1] / w


# ---------------------------------------------------------------- segmentacao


def mask_calcada(rgb, y_min):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    verde = (g > r + 6) & (g >= b)
    agua = (b > r + 12) & (b >= g)
    quente = (r >= g - 2) & (g >= b - 4)
    m = quente & ~verde & ~agua & (mx >= 70) & (sat < 0.45) & (mx > 95)
    m[:y_min, :] = False
    m = ndimage.binary_opening(m, np.ones((7, 7)))
    m = ndimage.binary_closing(m, np.ones((15, 15)))
    rot, n = ndimage.label(m)
    if n:
        sz = ndimage.sum(m, rot, range(1, n + 1))
        m = rot == (np.argmax(sz) + 1)
    return ndimage.binary_fill_holes(m)


def mask_azul(rgb, y_min):
    """Agua mais a casca de fibra, com folga. Usada no close, onde a
    calcada ocupa o quadro inteiro e o que sobra e so a piscina."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = (b > r + 10) & (b > g - 25)
    m[:y_min, :] = False
    m = ndimage.binary_closing(m, np.ones((9, 9)))
    rot, n = ndimage.label(m)
    if n:
        sz = ndimage.sum(m, rot, range(1, n + 1))
        m = rot == (np.argmax(sz) + 1)
    m = ndimage.binary_fill_holes(m)
    return ndimage.binary_dilation(m, np.ones((7, 7)))


def mask_piscina(rgb, y_min):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = (b > r + 25) & (g > r + 10) & (b > 110)
    m[:y_min, :] = False
    m = ndimage.binary_opening(m, np.ones((9, 9)))
    rot, n = ndimage.label(m)
    if n:
        sz = ndimage.sum(m, rot, range(1, n + 1))
        m = rot == (np.argmax(sz) + 1)
    return ndimage.binary_fill_holes(m)


def cantos_piscina(mask):
    ys, xs = np.nonzero(mask)
    pts = np.column_stack([xs, ys]).astype(float)
    hull = pts[ConvexHull(pts).vertices]
    melhor, melhor_a = None, -1.0
    for c in combinations(range(len(hull)), 4):
        q = hull[list(c)]
        x, y = q[:, 0], q[:, 1]
        a = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        if a > melhor_a:
            melhor, melhor_a = q, a
    c = melhor.mean(axis=0)
    q = melhor[np.argsort(np.arctan2(melhor[:, 1] - c[1], melhor[:, 0] - c[0]))]
    return np.roll(q, -int(np.argmin(q.sum(axis=1))), axis=0)


# ---------------------------------------------------------------- cenas

# Piscina de fibra: 6,0 x 3,0 m (a confirmar com trena).
PISCINA = (6.0, 3.0)

# Raio do canto da casca de fibra. Medido por proporcao nas fotos do local
# e coerente com os exemplos de fabricante enviados pelo proprietario.
CANTO_R = 0.18

# Largura do nariz boleado da peca de borda -- a parte curva que encara a
# agua. E nela que mora a leitura de volume: o topo pega o sol, a curva
# escurece descendo ate a lamina.
NARIZ_M = 0.055

# No close a piscina aparece so parcialmente, entao a homografia nao pode
# ser derivada dos 4 cantos como na panoramica.
# A, B e C vem de regressao sobre o
# contorno inferior da mascara azul, que e a aresta externa da fibra.
# A estimativa manual anterior errava a aresta direita em 226 px na ponta,
# e a faixa de borda saia deslocada desse lado.
#   esquerda: y = 0,5877x + 193,4     direita: y = -1,0504x + 1506,8
CLOSE_A = (801.7, 664.6)  # interseccao das duas arestas = canto externo
CLOSE_B = (95.0, 249.3)   # sobre a aresta de 6 m
CLOSE_C = (1300.0, 141.3) # sobre a aresta de 3 m
CLOSE_D = (593.3, -274.0) # fecha o retangulo; ajustado por conferencia visual
CLOSE_AB_M = 2.8          # metros ate B (escala calibrada pela paginacao)
CLOSE_AC_M = 2.5          # metros ate C

CENAS = {
    "pano": {
        "foto": "fotos/WhatsApp Image 2026-08-10 at 14.04.25.jpeg",
        "y_min": 470,
        "borda_m": 0.30,
        # A calcada e uma ilha cercada de grama: vale segmentar por cor.
        "modo_mascara": "cor",
        # Faixa da lamina de fibra a ser capeada pela peca de borda,
        # calibrada por conferencia visual ate o rebordo azul sumir.
        "lamina_m": 0.30,
        # As placas antigas sao pequenas em pixels; sigma menor ja as apaga.
        "sigma_luz": 18.0,
        "faixa_luz": (0.45, 1.32),
    },
    "close": {
        "foto": "fotos/WhatsApp Image 2026-08-10 at 14.04.24 (1).jpeg",
        "y_min": 0,
        "borda_m": 0.26,
        # Aqui a calcada ocupa o quadro inteiro; o robusto e recortar a
        # piscina e ficar com todo o resto.
        "modo_mascara": "complemento",
        "lamina_m": 0.40,
        # Placas antigas enormes em pixels: sem sigma alto, as juntas e
        # manchas viram borroes escuros no material novo.
        "sigma_luz": 75.0,
        "faixa_luz": (0.80, 1.14),
    },
}


def monta_cena(nome):
    cfg = CENAS[nome]
    im = Image.open(caminho(cfg["foto"])).convert("RGB")
    rgb = np.asarray(im).astype(np.int16)

    if cfg["modo_mascara"] == "cor":
        calcada = mask_calcada(rgb, cfg["y_min"])
        azul = mask_piscina(rgb, cfg["y_min"])
    else:
        azul = mask_azul(rgb, cfg["y_min"])
        calcada = ~azul

    if nome == "pano":
        pool = mask_piscina(rgb, cfg["y_min"])
        quad = cantos_piscina(pool)
        lados = [np.linalg.norm(quad[(i + 1) % 4] - quad[i]) for i in range(4)]
        L, W = PISCINA
        if lados[0] + lados[2] < lados[1] + lados[3]:
            L, W = W, L
        plano = np.array([[0, 0], [L, 0], [L, W], [0, W]], float)
        H = homografia(plano, quad)
        retangulo = (L, W)
    else:
        L, W = CLOSE_AB_M, CLOSE_AC_M
        plano = np.array([[0, 0], [L, 0], [L, W], [0, W]], float)
        quad = np.array([CLOSE_A, CLOSE_B, CLOSE_D, CLOSE_C], float)
        H = homografia(plano, quad)
        # A piscina ocupa o quadrante u>=0, v>=0 e sai do quadro.
        retangulo = (1e6, 1e6)

    Hinv = np.linalg.inv(H)
    U, V = coords_mundo(Hinv)

    # Distancia com sinal ate a casca da piscina, em metros: negativa dentro,
    # positiva na calcada. O canto e ARREDONDADO -- piscina de fibra sai da
    # forma com raio, e a peca de borda e cortada acompanhando essa curva.
    # (Uma versao anterior usava distancia de Chebyshev, que produz canto
    # vivo de meia-esquadria; isso vale para piscina de alvenaria retangular,
    # nao para esta.)
    L, W = retangulo
    r = CANTO_R
    if L > 1e5:                     # close: a piscina e o quadrante u,v > 0
        qx, qy = r - U, r - V
        # O termo `dentro` e indispensavel: sem ele a distancia satura em -r
        # e o fundo inteiro da piscina passa a contar como faixa de borda.
        d_sinal = (np.minimum(np.maximum(qx, qy), 0)
                   + np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) - r)
    else:                           # panoramica: retangulo de cantos redondos
        qx = np.abs(U - L / 2) - (L / 2 - r)
        qy = np.abs(V - W / 2) - (W / 2 - r)
        d_sinal = (np.minimum(np.maximum(qx, qy), 0)
                   + np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) - r)

    # Coordenada ao longo do perimetro, valida dos dois lados da aresta.
    perto_u = np.minimum(np.abs(U), np.abs(U - L))
    perto_v = np.minimum(np.abs(V), np.abs(V - W))
    ao_longo = np.where(perto_u < perto_v, V, U)

    lamina = cfg["lamina_m"]
    faixa = (d_sinal > -lamina) & (d_sinal < cfg["borda_m"])
    # Entre a calcada e a agua sobra um filete azul-acinzentado que a regra
    # de agua exclui da calcada e a regra de piscina nao captura. Fechar a
    # uniao sela essa fresta; sem isso ela fica sem pintar e o rebordo da
    # fibra reaparece como um fio azul contornando a peca de borda.
    regiao = ndimage.binary_closing(calcada | azul, np.ones((17, 17)))
    borda = faixa & regiao
    piso = calcada & ~borda

    return {
        "nome": nome,
        "foto": np.asarray(im).astype(np.float64),
        "calcada": calcada,
        "piso": piso,
        "borda": borda,
        "azul": azul,
        "U": U,
        "V": V,
        "d_sinal": d_sinal,
        "ao_longo": ao_longo,
        "borda_m": cfg["borda_m"],
        "lamina_m": lamina,
        "sigma_luz": cfg["sigma_luz"],
        "faixa_luz": cfg["faixa_luz"],
    }


# ---------------------------------------------------------------- ruido


def _hash01(i, j, semente):
    h = (i.astype(np.int64) * 374761393
         + j.astype(np.int64) * 668265263
         + np.int64(semente) * 1274126177)
    h = h.astype(np.uint64)
    h = (h ^ (h >> np.uint64(13))) * np.uint64(1274126177)
    h = h ^ (h >> np.uint64(16))
    return (h & np.uint64(0xFFFFFF)).astype(np.float64) / float(0xFFFFFF)


def ruido(U, V, freq_u, freq_v, semente):
    """Ruido de valor com interpolacao suave, avaliado em metros."""
    x, y = U * freq_u, V * freq_v
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    i, j = x0.astype(np.int64), y0.astype(np.int64)
    n00 = _hash01(i, j, semente)
    n10 = _hash01(i + 1, j, semente)
    n01 = _hash01(i, j + 1, semente)
    n11 = _hash01(i + 1, j + 1, semente)
    return (n00 * (1 - fx) * (1 - fy) + n10 * fx * (1 - fy)
            + n01 * (1 - fx) * fy + n11 * fx * fy)


def grao(tipo, U, V, semente):
    """Retorna modulacao de brilho em torno de 0, conforme o tipo de pedra."""
    if tipo == "pontilhado":            # granito flameado: cristais finos
        g = (ruido(U, V, 260, 260, semente) - 0.5) * 1.15
        g += (ruido(U, V, 70, 70, semente + 7) - 0.5) * 0.55
        return g
    if tipo == "camadas":               # quartzito: veios alongados
        g = (ruido(U, V, 12, 150, semente) - 0.5) * 1.30
        g += (ruido(U, V, 5, 40, semente + 3) - 0.5) * 0.75
        return g
    if tipo == "marmore":               # veio sinuoso, nao listra reta
        # Distorcer o dominio antes de amostrar e o que curva o veio. Ruido
        # direto sai em listras paralelas, que nao se parecem com marmore.
        # Distorcao fraca e de baixa frequencia: forte demais enrola o veio
        # em espiral e o resultado vira papel marmorizado, nao pedra.
        wx = (ruido(U, V, 1.1, 1.1, semente + 21) - 0.5) * 0.8
        wy = (ruido(U, V, 1.1, 1.1, semente + 37) - 0.5) * 0.8
        v = ruido(U + wx, V + wy, 2.6, 1.3, semente)
        veio = np.exp(-np.abs(v - 0.5) * 30.0)      # cristas finas e esparsas
        fino = (ruido(U, V, 45, 45, semente + 5) - 0.5) * 0.22
        return -veio * 0.55 + 0.10 + fino
    if tipo == "mesclado":              # porcelanato: manchado suave
        return (ruido(U, V, 14, 14, semente) - 0.5) * 0.75
    if tipo == "madeira":               # fibra longa no sentido da regua
        g = (ruido(U, V, 6, 210, semente) - 0.5) * 1.5
        g += (ruido(U, V, 3, 60, semente + 5) - 0.5) * 0.8
        return g
    return np.zeros_like(U)


# ---------------------------------------------------------------- textura


def textura(mat, U, V, semente=0):
    """Cor RGB do material nas coordenadas de mundo dadas."""
    tw, th = mat["placa_m"]
    junta = mat["junta_mm"] / 1000.0

    iu = np.floor(U / tw)
    iv = np.floor(V / th)
    fu = U / tw - iu
    fv = V / th - iv

    base = np.array(mat["cor_base"], float)
    cor = np.repeat(base[None, :], U.size, axis=0).reshape(U.shape + (3,))

    # Variacao de tom peca a peca. Amplitude baixa de proposito: valores
    # altos fazem placas vizinhas alternarem e a calcada vira tabuleiro.
    var = (_hash01(iu.astype(np.int64), iv.astype(np.int64), 91 + semente) - 0.5)
    cor = cor + (var * mat["cor_variacao"] * 0.7)[..., None]

    # Grao interno.
    g = grao(mat["grao"], U, V, 17 + semente)
    cor = cor * (1 + g * 0.16)[..., None]

    # Junta de assentamento.
    du = np.minimum(fu, 1 - fu) * tw
    dv = np.minimum(fv, 1 - fv) * th
    na_junta = (du < junta / 2) | (dv < junta / 2)
    cj = np.array(mat["cor_junta"], float)
    cor = np.where(na_junta[..., None], cj[None, None, :], cor)

    # Leve escurecimento junto a junta, que da relevo a peca.
    prox = np.exp(-np.minimum(du, dv) / 0.012)
    cor = cor * (1 - 0.10 * prox)[..., None]

    return np.clip(cor, 0, 255)


def textura_borda(mat, cena, semente=3):
    """Pecas de borda: juntas transversais ao longo do perimetro."""
    # d = 0 na lamina d'agua, crescendo para fora da piscina.
    d = cena["d_sinal"] + cena["lamina_m"]
    s = cena["ao_longo"]
    largura = cena["lamina_m"] + cena["borda_m"]
    junta = mat["junta_mm"] / 1000.0
    passo = 0.50                        # peca de 50 cm

    base = np.array(mat["cor_base"], float)
    iv = np.floor(s / passo)
    cor = np.repeat(base[None, :], d.size, axis=0).reshape(d.shape + (3,))
    var = (_hash01(iv.astype(np.int64), np.zeros_like(iv, dtype=np.int64),
                   57 + semente) - 0.5)
    cor = cor + (var * mat["cor_variacao"] * 1.6)[..., None]

    # Grao nas coordenadas de mundo, nao nas do perimetro: usar (s, d)
    # estica o cristal do granito ao longo da faixa.
    g = grao(mat["grao"], cena["U"], cena["V"], 31 + semente)
    cor = cor * (1 + g * 0.14)[..., None]

    ds = np.minimum(s / passo - iv, 1 - (s / passo - iv)) * passo
    na_junta = (ds < junta / 2) | (d > largura - junta / 2)
    cj = np.array(mat["cor_junta"], float)
    cor = np.where(na_junta[..., None], cj[None, None, :], cor)

    # ---- volume da peca -------------------------------------------------
    # Sem isto a borda vira uma faixa de cor chapada, que e exatamente o que
    # denuncia a montagem como recorte. A peca tem duas faces: o nariz
    # boleado, que encara a agua e recebe luz rasante, e o topo, que encara
    # o ceu. Modelo de cilindro: a normal gira da lateral para a vertical ao
    # longo do nariz.
    a = np.clip(d / NARIZ_M, 0, 1)
    lambert = 0.46 + 0.60 * np.sin(a * np.pi / 2)
    especular = 0.26 * np.exp(-((a - 0.74) ** 2) / 0.014)
    fator = np.where(d < NARIZ_M, lambert + especular, 1.0)

    # Sombra de contato onde a peca encosta no piso: o mesmo desnivel de
    # poucos milimetros que existe na obra real.
    fim = largura - 0.06
    fator = fator * (1 - 0.13 * np.clip((d - fim) / 0.06, 0, 1))

    cor = cor * fator[..., None]
    return np.clip(cor, 0, 255)


# ---------------------------------------------------------------- composicao


def campo_de_luz(foto, mask, sigma, faixa):
    """Iluminacao da cena, sem a textura antiga: desfoque da luminancia.

    O sigma precisa ser maior que as feicoes do piso antigo. Se for pequeno,
    junta e mancha da Sao Tome sobrevivem ao desfoque e reaparecem como
    borroes escuros sob o material novo.
    """
    lum = foto @ np.array([0.299, 0.587, 0.114])
    m = mask.astype(float)
    # Desfoque normalizado para a luz de fora da mascara nao vazar para dentro.
    num = ndimage.gaussian_filter(lum * m, sigma)
    den = ndimage.gaussian_filter(m, sigma)
    campo = np.where(den > 1e-6, num / np.maximum(den, 1e-6), lum)
    ref = np.percentile(campo[mask], 70) if mask.any() else 1.0
    return np.clip(campo / max(ref, 1e-6), *faixa)


def compoe(cena, mat_piso, mat_borda):
    foto = cena["foto"]
    saida = foto.copy()
    sigma, faixa = cena["sigma_luz"], cena["faixa_luz"]

    luz_piso = campo_de_luz(foto, cena["piso"], sigma, faixa)
    luz_borda = campo_de_luz(foto, cena["borda"], sigma, faixa)

    tex_piso = textura(mat_piso, cena["U"], cena["V"])
    tex_borda = textura_borda(mat_borda, cena)

    novo = np.where(cena["borda"][..., None],
                    tex_borda * luz_borda[..., None],
                    tex_piso * luz_piso[..., None])

    # ---- o que a peca faz ao redor dela ---------------------------------
    # Uma peca de borda nao termina no proprio contorno: ela projeta sombra
    # na agua, se reflete nela e escurece o piso onde encosta. Sem isso a
    # pedra parece flutuar recortada sobre a foto.
    d_sinal, lamina = cena["d_sinal"], cena["lamina_m"]

    # Distancia para dentro da agua, a partir da lamina.
    dentro_agua = np.maximum(-(d_sinal + lamina), 0)
    agua = cena["azul"] & (d_sinal < -lamina)

    # Sombra projetada: a linha escura logo abaixo do avanco da peca.
    sombra = 1 - 0.46 * np.exp(-dentro_agua / 0.055)
    # Reflexo da pedra na agua, logo depois da sombra.
    brilho = 0.14 * np.exp(-((dentro_agua - 0.14) ** 2) / 0.012)
    clara = np.array([235, 240, 242], float)

    saida = np.where(agua[..., None],
                     np.clip(saida * sombra[..., None]
                             + clara * brilho[..., None], 0, 255),
                     saida)

    # Sombra de contato no piso, do lado de fora da peca.
    fora_peca = d_sinal - cena["borda_m"]
    contato = 1 - 0.16 * np.exp(-np.maximum(fora_peca, 0) / 0.045)
    no_piso = cena["piso"] & (fora_peca >= 0)
    novo = np.where(no_piso[..., None], novo * contato[..., None], novo)

    # Uniao com a borda, nao so a calcada: a faixa de borda invade a lamina
    # de fibra, que esta fora da mascara de calcada. Usar so a calcada aqui
    # deixa o rebordo azul reaparecer por baixo da peca.
    pintado = cena["calcada"] | cena["borda"]
    # Suavizada para nao serrilhar contra a grama e contra a agua.
    alpha = ndimage.gaussian_filter(pintado.astype(float), 0.9)[..., None]
    saida = saida * (1 - alpha) + np.clip(novo, 0, 255) * alpha
    return np.clip(saida, 0, 255).astype(np.uint8)


def _dados(rel="deck/materiais.json"):
    with open(caminho(rel), encoding="utf-8") as f:
        return json.load(f)


def carrega_materiais(rel="deck/materiais.json"):
    """Materiais de piso."""
    return _dados(rel)["materiais"]


def carrega_bordas(rel="deck/materiais.json"):
    """Materiais da peca de borda. Lista separada porque os criterios sao
    outros: o que importa numa borda e aderencia molhada, resistencia ao
    cloro e possibilidade de peca sob medida, nao a area de piso."""
    bordas = _dados(rel)["bordas"]
    for b in bordas:
        # A peca de borda nao tem paginacao propria a declarar: a junta
        # transversal a cada 50 cm ja vem de textura_borda. Estes valores
        # so completam o que a funcao de textura espera.
        b.setdefault("placa_m", [0.50, 0.30])
        b.setdefault("junta_mm", 3)
        b.setdefault("cor_junta",
                     [int(c * 0.80) for c in b["cor_base"]])
    return bordas
