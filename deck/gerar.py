"""Gera todas as imagens do deck.

Saida em deck/render/:
  pano_<id>.jpg      montagem na panoramica
  close_<id>.jpg     montagem no close da borda
  mini_<id>.jpg      recorte da panoramica para a tela de comparacao
  amostra_<id>.jpg   amostra do material vista de cima
  diagnostico.jpg    close com as marcacoes dos tres problemas
  perfis.png         os quatro perfis de borda em corte
  capa.jpg           foto de capa
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import montagem as M

SAIDA = M.caminho("deck/render")
CAPA = M.caminho("fotos/WhatsApp Image 2026-08-10 at 14.04.25 (1).jpeg")

# Quando o material nao serve como borda, a montagem usa granito cinza --
# e o slide diz isso em texto, para a imagem nunca prometer o impossivel.
BORDA_ALTERNATIVA = "granito-cinza-andorinha"

# Recorte usado na tela de comparacao: piscina mais calcada, sem o excesso
# de ceu e de casa, para a cor do piso ocupar o maximo do quadro.
RECORTE_MINI = (330, 430, 1290, 1150)

# Recorte do close centrado no canto da piscina: e ali que a peca de borda
# encontra a lamina de fibra, que e o assunto da secao da borda.
RECORTE_BORDA = (170, 40, 1490, 830)

# Piso mantido constante nas comparacoes de borda, para so a borda variar.
PISO_NEUTRO = "granito-cinza-andorinha"

# As tres combinacoes finalistas do slide de recomendacao.
COMBOS = [
    ("equilibrio", "granito-branco-itaunas", "granito-branco-itaunas",
     "Equilíbrio geral"),
    ("conforto", "quartzito-branco-goias", "granito-branco-itaunas",
     "Conforto máximo ao pé"),
    ("manutencao", "porcelanato-pedra", "granito-cinza-andorinha",
     "Menor manutenção"),
]


def fonte(tam, negrito=False):
    nome = "arialbd.ttf" if negrito else "arial.ttf"
    for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
        p = os.path.join(base, nome)
        if os.path.exists(p):
            return ImageFont.truetype(p, tam)
    return ImageFont.load_default()


# ------------------------------------------------------------------ amostra


def amostra(mat, larg=1000, alt=620, metros=2.2):
    """Vista de cima do material, sem perspectiva."""
    v, u = np.mgrid[0:alt, 0:larg].astype(float)
    escala = metros / larg
    U, V = u * escala, v * escala
    cor = M.textura(mat, U, V)

    # Vinheta suave, so para a amostra nao parecer um retangulo chapado.
    yy, xx = np.mgrid[0:alt, 0:larg].astype(float)
    d = np.hypot((xx - larg / 2) / (larg / 2), (yy - alt / 2) / (alt / 2))
    cor = cor * np.clip(1.06 - 0.13 * d, 0, 2)[..., None]
    return Image.fromarray(np.clip(cor, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ perfis


def perfis_borda(larg=1560, alt=480):
    """Os quatro perfis de borda em corte.

    O desenho existe para mostrar dois detalhes que nenhuma foto mostra:
    a peca avanca sobre a lamina da fibra (com pingadeira por baixo) e a
    interface com a fibra e selada com junta flexivel, nunca rejunte rigido.
    """
    im = Image.new("RGB", (larg, alt), (255, 255, 255))
    d = ImageDraw.Draw(im)
    f_tit = fonte(24, True)
    f_not = fonte(18)
    f_lab = fonte(16)

    AGUA = (150, 210, 228)
    FIBRA = (92, 168, 200)
    PECA = (168, 164, 157)
    PISO = (203, 199, 191)
    BASE = (228, 225, 219)
    LINHA = (55, 55, 58)
    LARANJA = (206, 92, 52)

    nomes = ["Meia-cana (boleado)", "Cabeça de touro",
             "Reta viva", "Com canaleta"]
    notas = ["RECOMENDADO. Confortável de\nsentar e de apoiar o braço\nsaindo da água",
             "Boleado mais cheio. Combina\ncom a linguagem rústica\nda casa",
             "Aresta viva. Bonita em foto,\nmachuca joelho e canela.\nEntra com ressalva",
             "Transbordo pelo perímetro.\nExige mexer na hidráulica:\nprovavelmente fora de escopo"]

    lc = larg // 4
    TOPO, ESP = 150, 46          # topo da peca e sua espessura
    FUNDO = 300                  # ate onde descem agua e contrapiso

    for i in range(4):
        x0 = i * lc
        d.text((x0 + 26, 8), f"{i + 1}. {nomes[i]}", font=f_tit, fill=(20, 20, 22))
        for j, ln in enumerate(notas[i].split("\n")):
            d.text((x0 + 26, 330 + j * 24), ln, font=f_not, fill=(88, 88, 94))

        xa = x0 + 26                 # inicio da agua
        xf = x0 + 118                # face interna da casca de fibra
        xfe = xf + 16                # face externa da casca
        xp0 = xf - 26                # a peca avanca 26 px sobre a agua
        xp1 = x0 + lc - 96           # fim da peca de borda
        xd1 = x0 + lc - 22           # fim do trecho de piso desenhado

        # Agua e casca de fibra.
        d.rectangle([xa, TOPO + ESP, xf, FUNDO], fill=AGUA)
        d.rectangle([xf, TOPO + ESP - 16, xfe, FUNDO], fill=FIBRA)

        # Contrapiso sob a peca e sob o piso.
        d.rectangle([xfe, TOPO + ESP, xd1, TOPO + ESP + 30], fill=BASE)
        d.rectangle([xfe, TOPO + ESP + 30, xd1, FUNDO], fill=(240, 238, 234))

        # Piso da calcada, ja com caimento de 1 a 1,5% para fora da piscina.
        d.polygon([(xp1, TOPO + ESP - 30), (xd1, TOPO + ESP - 16),
                   (xd1, TOPO + ESP + 10), (xp1, TOPO + ESP + 6)],
                  fill=PISO, outline=LINHA)

        # A peca de borda.
        if i == 0:                                  # meia-cana
            d.rectangle([xp0 + 26, TOPO, xp1, TOPO + ESP], fill=PECA, outline=LINHA)
            d.pieslice([xp0, TOPO, xp0 + 52, TOPO + ESP], 90, 270,
                       fill=PECA, outline=LINHA)
        elif i == 1:                                # cabeca de touro
            d.rectangle([xp0 + 30, TOPO, xp1, TOPO + ESP], fill=PECA, outline=LINHA)
            d.ellipse([xp0 - 10, TOPO - 9, xp0 + 62, TOPO + ESP + 9],
                      fill=PECA, outline=LINHA)
        elif i == 2:                                # reta viva
            d.rectangle([xp0, TOPO, xp1, TOPO + ESP], fill=PECA, outline=LINHA)
        else:                                       # com canaleta
            meio = xp0 + 78
            d.rectangle([xp0, TOPO, meio, TOPO + ESP], fill=PECA, outline=LINHA)
            d.rectangle([meio + 30, TOPO, xp1, TOPO + ESP], fill=PECA, outline=LINHA)
            d.rectangle([meio, TOPO + 10, meio + 30, TOPO + ESP],
                        fill=(236, 243, 247), outline=LINHA)
            d.text((meio - 22, TOPO - 30), "canaleta", font=f_lab, fill=(70, 100, 120))

        # Pingadeira: sulco na face inferior do avanco. Escuro de proposito --
        # em branco o sulco some contra a peca.
        if i < 3:
            gx = xp0 + 32
            d.rectangle([gx, TOPO + ESP - 13, gx + 16, TOPO + ESP],
                        fill=(78, 74, 70), outline=LINHA)
            d.line([(gx + 8, TOPO + ESP + 2), (gx - 34, TOPO + ESP + 42)],
                   fill=(110, 70, 60), width=2)
            d.text((gx - 96, TOPO + ESP + 46), "pingadeira", font=f_lab,
                   fill=(110, 70, 60))

        # Junta flexivel entre a peca e a fibra: o detalhe que mais falha.
        d.line([(xfe - 3, TOPO + ESP), (xfe - 3, TOPO + ESP - 20)],
               fill=LARANJA, width=7)
        if i == 0:
            d.line([(xfe + 2, TOPO + ESP - 14), (xfe + 96, TOPO - 46)],
                   fill=LARANJA, width=2)
            d.text((xfe + 100, TOPO - 74), "junta flexível", font=f_lab,
                   fill=LARANJA)
            d.text((xfe + 100, TOPO - 56), "(mastique PU, nunca rejunte)",
                   font=f_lab, fill=LARANJA)

    d.text((26, alt - 30), "Corte esquemático, fora de escala. Em todos os "
           "perfis a peça avança 2–3 cm sobre a lâmina da fibra.",
           font=fonte(16), fill=(150, 150, 155))
    return im


# ------------------------------------------------------------------ diagnostico


def diagnostico():
    im = Image.open(M.caminho(M.CENAS["close"]["foto"])).convert("RGB")
    d = ImageDraw.Draw(im)
    f = fonte(46, True)
    marcas = [("1", (980, 470)), ("2", (975, 1010)), ("3", (250, 700))]
    for txt, (x, y) in marcas:
        d.ellipse([x - 34, y - 34, x + 34, y + 34],
                  fill=(200, 40, 40), outline=(255, 255, 255), width=4)
        cx = d.textbbox((0, 0), txt, font=f)
        d.text((x - (cx[2] - cx[0]) / 2, y - (cx[3] - cx[1]) / 2 - 6),
               txt, font=f, fill=(255, 255, 255))
    return im


# ------------------------------------------------------------------ principal


def main():
    os.makedirs(SAIDA, exist_ok=True)
    mats = M.carrega_materiais()
    por_id = {m["id"]: m for m in mats}

    print("montando cenas...")
    cenas = {n: M.monta_cena(n) for n in ("pano", "close")}

    Image.open(CAPA).convert("RGB").save(f"{SAIDA}/capa.jpg", quality=90)
    diagnostico().save(f"{SAIDA}/diagnostico.jpg", quality=90)
    perfis_borda().save(f"{SAIDA}/perfis.png")

    for m in mats:
        mid = m["id"]
        borda = m if m["borda"] != "nao" else por_id[BORDA_ALTERNATIVA]

        for cn, cena in cenas.items():
            img = Image.fromarray(M.compoe(cena, m, borda))
            img.save(f"{SAIDA}/{cn}_{mid}.jpg", quality=88)
            if cn == "pano":
                img.crop(RECORTE_MINI).resize((640, 480), Image.LANCZOS) \
                   .save(f"{SAIDA}/mini_{mid}.jpg", quality=86)

        amostra(m).save(f"{SAIDA}/amostra_{mid}.jpg", quality=92)
        print(f"  {m['n']:2d}. {m['nome']}")

    # ---- A borda como assunto proprio -------------------------------
    # Piso mantido igual em todas: so a peca de borda muda, senao a
    # comparacao mistura duas variaveis.
    print("bordas...")
    neutro = por_id[PISO_NEUTRO]
    Image.fromarray(M.compoe(cenas["close"], neutro, neutro)) \
        .crop(RECORTE_BORDA).save(f"{SAIDA}/borda_referencia.jpg", quality=90)
    Image.open(M.caminho(M.CENAS["close"]["foto"])).convert("RGB") \
        .crop(RECORTE_BORDA).save(f"{SAIDA}/borda_antes.jpg", quality=90)

    for b in M.carrega_bordas():
        img = Image.fromarray(M.compoe(cenas["close"], neutro, b))
        img.crop(RECORTE_BORDA).save(f"{SAIDA}/borda_{b['id']}.jpg", quality=90)
        amostra(b, metros=1.1).save(f"{SAIDA}/amostra_{b['id']}.jpg", quality=92)
        print(f"  {b['n']}. {b['nome']}")

    print("combinacoes finalistas...")
    for slug, id_piso, id_borda, rotulo in COMBOS:
        img = Image.fromarray(
            M.compoe(cenas["pano"], por_id[id_piso], por_id[id_borda]))
        img.crop(RECORTE_MINI).resize((760, 570), Image.LANCZOS) \
           .save(f"{SAIDA}/combo_{slug}.jpg", quality=88)
        print(f"  {rotulo}")

    print(f"\nimagens em {SAIDA}/")


if __name__ == "__main__":
    main()
