"""Gera a versão web do deck, com as mesmas imagens do PPTX.

Página única, autocontida (imagens embutidas em base64), com um comparador
interativo que troca os 10 materiais na mesma foto -- que é justamente o
que o PPTX não consegue fazer.
"""
import base64
import html
import io
import os

from PIL import Image

import montagem as M
from gerar import SAIDA, COMBOS, BORDA_ALTERNATIVA
from build_pptx import CRITERIOS, SELO, faixa_preco

DESTINO = M.caminho("deck/piscina-menor.html")


def b64(arquivo, largura=None, q=80):
    """Embute a imagem. As do PPTX estao em resolucao de impressao; para a
    web sao reduzidas, senao a pagina passa de 25 MB."""
    caminho = os.path.join(SAIDA, arquivo)
    if arquivo.endswith(".png"):
        with open(caminho, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    im = Image.open(caminho).convert("RGB")
    if largura and im.width > largura:
        im = im.resize((largura, round(im.height * largura / im.width)),
                       Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def e(t):
    return html.escape(str(t))


def pips(nota):
    return "".join(
        f'<i class="pip{" on" if i < nota else ""}"></i>' for i in range(5))


def selo(chave):
    rot, _ = SELO[chave]
    return f'<span class="selo {chave}">{e(rot)}</span>'


CSS = """
:root{
  --tinta:#1a1a1c; --suave:#70707a; --acento:#1e6f84; --creme:#f4f2ee;
  --linha:#e2dfd9; --alerta:#a8382a; --verde:#3f6b46; --ambar:#b57a1f;
  --fundo:#ffffff; --cartao:#ffffff; --escuro:#122a33;
}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --tinta:#ececef; --suave:#a0a0aa; --acento:#63b8cc; --creme:#1c1f22;
    --linha:#33383c; --alerta:#e2705f; --verde:#7fb98a; --ambar:#d9a24a;
    --fundo:#121416; --cartao:#191c1f; --escuro:#0d1e25;
  }
}
:root[data-theme="dark"]{
  --tinta:#ececef; --suave:#a0a0aa; --acento:#63b8cc; --creme:#1c1f22;
  --linha:#33383c; --alerta:#e2705f; --verde:#7fb98a; --ambar:#d9a24a;
  --fundo:#121416; --cartao:#191c1f; --escuro:#0d1e25;
}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--tinta);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
img{max-width:100%;display:block}
.env{max-width:1180px;margin:0 auto;padding:0 20px}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;font-weight:700;
  line-height:1.2;margin:0}
.capa{position:relative;color:#fff}
.capa img{width:100%;height:min(62vh,540px);object-fit:cover}
.capa .txt{background:var(--escuro);padding:26px 0 30px}
.capa h1{font-size:clamp(26px,4.2vw,42px)}
.capa p{margin:8px 0 0;color:#c9dae0}
.capa .loc{color:#91aab4;font-size:14px;margin-top:10px}
section{padding:52px 0;border-top:1px solid var(--linha)}
section>.env>h2{font-size:clamp(22px,3vw,30px);margin-bottom:6px}
.sub{color:var(--suave);margin:0 0 26px}
.grade{display:grid;gap:18px}
.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.cartao{background:var(--creme);border-radius:6px;padding:18px 20px}
.cartao h3{font-size:15px;font-family:inherit;margin-bottom:6px}
.cartao p{margin:0;color:var(--suave);font-size:14px}
.mat{border-top:1px solid var(--linha);padding:44px 0}
.mat-cab{display:flex;flex-wrap:wrap;gap:14px;align-items:baseline;
  justify-content:space-between;margin-bottom:18px}
.mat-num{font-family:Georgia,serif;font-size:30px;color:var(--acento);
  font-weight:700;margin-right:12px}
.mat-nome{font-family:Georgia,serif;font-size:clamp(20px,2.6vw,27px);
  font-weight:700}
.mat-fam{color:var(--suave);font-size:14px;margin-top:2px}
.mat-preco{text-align:right;font-weight:600}
.mat-preco small{display:block;font-weight:400;color:var(--suave);font-size:12px}
.fotos{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.fotos figcaption{color:var(--suave);font-size:12.5px;font-style:italic;
  margin-top:6px}
.ficha{display:grid;gap:22px;margin-top:22px;
  grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.crit{display:flex;align-items:center;gap:10px;font-size:13.5px;margin:5px 0}
.crit span{flex:1}
.pip{width:15px;height:9px;border-radius:1px;background:var(--linha);
  display:inline-block;margin-right:3px}
.pip.on{background:var(--acento)}
.selo{display:inline-block;padding:2px 9px;border-radius:3px;color:#fff;
  font-size:11.5px;font-weight:700}
.selo.sim{background:var(--verde)} .selo.limitado{background:var(--ambar)}
.selo.nao{background:var(--alerta)}
.rot{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.aviso{background:var(--alerta);color:#fff;padding:10px 14px;border-radius:4px;
  font-size:13.5px;font-weight:600;margin-top:14px}
.tab-env{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;min-width:860px;font-size:13.5px}
th{background:var(--escuro);color:#fff;padding:10px 8px;text-align:center;
  font-size:12px;position:sticky;top:0}
th:nth-child(2){text-align:left}
td{padding:9px 8px;text-align:center;border-bottom:1px solid var(--linha)}
td:nth-child(2){text-align:left;font-weight:600}
tbody tr:nth-child(even){background:var(--creme)}
.n1,.n2{color:var(--alerta);font-weight:700}
.n4,.n5{color:var(--verde);font-weight:700}
.comp{display:grid;gap:20px;grid-template-columns:minmax(0,2fr) minmax(220px,1fr)}
@media(max-width:820px){.comp{grid-template-columns:1fr}}
.comp-foto{position:relative;border-radius:6px;overflow:hidden}
.comp-foto img{width:100%}
.opts{display:flex;flex-direction:column;gap:4px;max-height:520px;overflow:auto}
.opt{display:flex;gap:10px;align-items:center;padding:7px 9px;border:0;
  background:transparent;border-radius:5px;cursor:pointer;text-align:left;
  font:inherit;font-size:13.5px;color:var(--tinta);width:100%}
.opt:hover{background:var(--creme)}
.opt[aria-pressed="true"]{background:var(--acento);color:#fff}
.opt .sw{width:34px;height:26px;border-radius:3px;flex:none;
  border:1px solid rgba(0,0,0,.15);background-size:cover}
.opt b{font-weight:600}
.opt small{display:block;opacity:.75;font-size:11.5px}
.rodape{padding:34px 0 60px;color:var(--suave);font-size:13px}
.limite{background:var(--creme);border-radius:6px;padding:18px 20px;
  margin-top:22px;font-size:13.5px}
.limite li{margin:5px 0;color:var(--suave)}
"""

JS = """
(function(){
  // As fotos ja estao na pagina, uma por material. O comparador reaproveita
  // essas mesmas imagens em vez de embutir uma segunda copia em base64.
  var fotos = JSON.parse(document.getElementById('dados').textContent);
  var img = document.getElementById('comp-img');
  var nome = document.getElementById('comp-nome');
  var botoes = Array.prototype.slice.call(
    document.querySelectorAll('.opt'));
  function escolhe(i){
    var origem = document.getElementById('pano-' + fotos[i].id);
    img.src = origem.currentSrc || origem.src;
    nome.textContent = fotos[i].nome + ' — R$ ' + fotos[i].preco + '/m²';
    botoes.forEach(function(b,j){
      b.setAttribute('aria-pressed', j === i ? 'true' : 'false');
    });
  }
  botoes.forEach(function(b,i){
    b.addEventListener('click', function(){ escolhe(i); });
  });
  escolhe(0);
})();
"""


def bloco_material(m, por_id):
    mid = m["id"]
    alerta = (f'<div class="aviso">▲ {e(m["alerta"])}</div>'
              if m["alerta"] else "")
    nota_borda = ""
    if m["borda"] == "nao":
        nota_borda = (f'<figcaption style="color:var(--alerta)">Borda mostrada '
                      f'em {e(por_id[BORDA_ALTERNATIVA]["nome"])} — este '
                      f'material não serve como borda.</figcaption>')
    crits = "".join(
        f'<div class="crit"><span>{e(rot)}</span>{pips(m["criterios"][k])}</div>'
        for k, rot in CRITERIOS)
    return f"""
<article class="mat" id="m-{mid}">
 <div class="env">
  <div class="mat-cab">
   <div><span class="mat-num">{m['n']:02d}</span>
     <span class="mat-nome">{e(m['nome'])}</span>
     <div class="mat-fam">{e(m['familia'])} · {e(m['subtitulo'])}</div></div>
   <div class="mat-preco">R$ {m['preco_m2'][0]}–{m['preco_m2'][1]} /m²
     <small>{faixa_preco(m)} · faixa indicativa, confirmar local</small></div>
  </div>
  {alerta}
  <div class="fotos">
   <figure style="margin:0"><img id="pano-{mid}" src="{b64(f'pano_{mid}.jpg', 1200)}"
     alt="Vista geral com {e(m['nome'])}" loading="lazy">
     <figcaption>Vista geral da área</figcaption></figure>
   <figure style="margin:0"><img src="{b64(f'close_{mid}.jpg', 1100)}"
     alt="Detalhe da borda com {e(m['nome'])}" loading="lazy">
     <figcaption>Detalhe da borda e do encontro com a fibra</figcaption>
     {nota_borda}</figure>
  </div>
  <div class="ficha">
   <div><img src="{b64(f'amostra_{mid}.jpg', 520)}" alt="Amostra"
      style="border-radius:4px" loading="lazy">
     <div class="mat-fam" style="text-align:center">amostra</div></div>
   <div>{crits}</div>
   <div><div class="rot" style="color:var(--suave)">Aplicação</div>
     <p style="margin:8px 0">Borda {selo(m['borda'])}<br><br>
        Piso {selo(m['piso'])}</p></div>
   <div><p style="margin:0 0 10px;font-weight:600">{e(m['resumo'])}</p>
     <div class="rot" style="color:var(--verde)">A favor</div>
     <p style="margin:2px 0 10px;color:var(--suave);font-size:13.5px">
       {e(m['a_favor'])}</p>
     <div class="rot" style="color:var(--alerta)">Contra</div>
     <p style="margin:2px 0;color:var(--suave);font-size:13.5px">
       {e(m['contra'])}</p></div>
  </div>
 </div>
</article>"""


def main():
    mats = M.carrega_materiais()
    por_id = {m["id"]: m for m in mats}

    ordem = sorted(mats, key=lambda m: sum(m["preco_m2"]) / 2)
    linhas = ""
    for m in ordem:
        cels = "".join(
            f'<td class="n{m["criterios"][k]}">{m["criterios"][k]}</td>'
            for k, _ in CRITERIOS)
        linhas += (f"<tr><td>{m['n']}</td><td>{e(m['nome'])}</td>{cels}"
                   f"<td>{m['preco_m2'][0]}–{m['preco_m2'][1]}</td>"
                   f"<td>{selo(m['borda'])}</td><td>{selo(m['piso'])}</td></tr>")

    opts, dados = "", []
    for i, m in enumerate(mats):
        opts += (f'<button class="opt" aria-pressed="false">'
                 f'<span class="sw" style="background-image:url('
                 f'{b64(f"amostra_{m["id"]}.jpg", 120, 78)})"></span>'
                 f'<span><b>{m["n"]:02d} {e(m["nome"])}</b>'
                 f'<small>R$ {m["preco_m2"][0]}–{m["preco_m2"][1]}/m²</small>'
                 f'</span></button>')
        dados.append({"id": m["id"], "nome": m["nome"],
                      "preco": f'{m["preco_m2"][0]}–{m["preco_m2"][1]}'})

    import json as _json
    combos = ""
    for slug, id_piso, id_borda, rotulo in COMBOS:
        combos += (f'<div class="cartao"><h3 style="font-family:Georgia,serif;'
                   f'font-size:19px">{e(rotulo)}</h3>'
                   f'<img src="{b64(f"combo_{slug}.jpg", 720)}" alt="{e(rotulo)}" '
                   f'style="border-radius:4px;margin:12px 0" loading="lazy">'
                   f'<p style="color:var(--acento);font-weight:600">'
                   f'Piso: {e(por_id[id_piso]["nome"])}<br>'
                   f'Borda: {e(por_id[id_borda]["nome"])}</p></div>')

    doc = f"""<meta charset="utf-8">
<title>Piscina menor — troca de borda e calçada</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<header class="capa">
  <img src="{b64('capa.jpg', 1500, 82)}" alt="A piscina menor e a casa ao fundo">
  <div class="txt"><div class="env">
    <h1>Piscina menor — troca de borda e calçada</h1>
    <p>10 materiais aplicados sobre as fotos do local</p>
    <div class="loc">Ponta da Fruta, Vila Velha — ES · agosto de 2026</div>
  </div></div>
</header>

<section><div class="env">
  <h2>O que existe hoje</h2>
  <p class="sub">O defeito principal não é o piso: é a ausência de peça de borda.</p>
  <div class="grade g2">
    <figure style="margin:0"><img src="{b64('diagnostico.jpg', 1200)}"
      alt="Close do canto com as marcações" style="border-radius:6px">
      <figcaption class="mat-fam">Detalhe do canto: a fibra termina e sobra
        concreto bruto até a pedra.</figcaption></figure>
    <div class="grade">
      <div class="cartao"><h3>1 · Não existe peça de borda</h3>
        <p>A casca de fibra termina e sobra uma faixa de concreto bruto até a
           pedra. Responde pela maior parte da sensação de malacabado.</p></div>
      <div class="cartao"><h3>2 · Rejunte largo, manchado, com mato</h3>
        <p>Degrada mais a percepção da área do que o desgaste da pedra em si.</p></div>
      <div class="cartao"><h3>3 · Duas paginações misturadas</h3>
        <p>Placa serrada regular na maior parte e caco irregular junto à
           piscina, sem transição.</p></div>
      <div class="cartao"><h3>Levantamento estimado</h3>
        <p>Piscina ~6,0 × 3,0 m · calçada de 1,5 a 2,5 m no perímetro<br>
           Piso: 60 a 75 m² · Borda: ~18 m lineares<br>
           <em>Estimado por foto — confirmar com trena.</em></p></div>
    </div>
  </div>
</div></section>

<section><div class="env">
  <h2>O que muda</h2>
  <p class="sub">Sai a São Tomé inteira. Entram borda nova e piso novo, sobre
     contrapiso regularizado.</p>
  <img src="{b64('perfis.png')}" alt="Os quatro perfis de borda em corte"
       style="border-radius:6px">
  <h3 style="margin:30px 0 14px;font-size:19px">Seis detalhes que separam obra
     boa de obra que estraga em dois anos</h3>
  <div class="grade g3">
    <div class="cartao"><h3>A borda avança 2–3 cm sobre a fibra, com pingadeira</h3>
      <p>Sem o sulco, a água escorre pela face e mancha.</p></div>
    <div class="cartao"><h3>Junta flexível na interface, nunca rejunte rígido</h3>
      <p>A fibra trabalha com temperatura; rejunte duro trinca.</p></div>
    <div class="cartao"><h3>Caimento de 1 a 1,5% para fora da piscina</h3>
      <p>Hoje a água suja da calçada volta para dentro.</p></div>
    <div class="cartao"><h3>Rejunte epóxi, não cimentício</h3>
      <p>Resiste ao cloro, não mancha e não cria limo.</p></div>
    <div class="cartao"><h3>Juntas de dilatação a cada ~3 m</h3>
      <p>Em 60–75 m² de sol pleno, sem elas o piso estufa.</p></div>
    <div class="cartao"><h3>Ferragem em inox 316 (A4), não A2</h3>
      <p>Litoral: A2 mancha de ferrugem no primeiro ano.</p></div>
  </div>
</div></section>

<section style="padding-bottom:0"><div class="env">
  <h2>Os dez materiais</h2>
  <p class="sub">Cinco quadrados cheios é sempre o melhor. Em «Custo baixo»,
     cinco significa mais barato.</p>
</div></section>
{''.join(bloco_material(m, por_id) for m in mats)}

<section><div class="env">
  <h2>Os dez lado a lado</h2>
  <p class="sub">Ordenado do mais barato para o mais caro.</p>
  <div class="tab-env"><table>
   <thead><tr><th>#</th><th>Material</th>
   {''.join(f'<th>{e(r)}</th>' for _, r in CRITERIOS)}
   <th>R$/m²</th><th>Borda</th><th>Piso</th></tr></thead>
   <tbody>{linhas}</tbody></table></div>
</div></section>

<section><div class="env">
  <h2>Comparador</h2>
  <p class="sub">Clique num material para trocá-lo na foto.</p>
  <div class="comp">
    <div>
      <div class="comp-foto"><img id="comp-img" src="" alt="Montagem"></div>
      <p id="comp-nome" style="margin:10px 0 0;font-weight:600"></p>
    </div>
    <div class="opts">{opts}</div>
  </div>
</div></section>

<section><div class="env">
  <h2>Três combinações que eu levaria adiante</h2>
  <p class="sub">Borda e piso escolhidos juntos. Todas com borda em meia-cana.</p>
  <div class="grade g3">{combos}</div>
</div></section>

<footer class="rodape"><div class="env">
  <div class="limite">
    <strong>O que estas imagens são e o que não são</strong>
    <ul>
      <li>São estudo de acabamento, não renderização fotorrealista: comunicam
          cor, contraste e paginação, não reflexo nem sombra recalculada.</li>
      <li>Cor de pedra natural varia por lote. Peça amostra física e veja a
          placa sob o sol do local, molhada e seca, antes de fechar.</li>
      <li>Preços são faixas indicativas para a Grande Vitória/ES, a confirmar
          com fornecedor local.</li>
      <li>Área estimada por foto: 60 a 75 m² de piso e ~18 m de borda.
          Confirmar com trena.</li>
    </ul>
  </div>
</div></footer>

<script type="application/json" id="dados">{_json.dumps(dados)}</script>
<script>{JS}</script>
"""
    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write(doc)
    mb = os.path.getsize(DESTINO) / 1e6
    print(f"{DESTINO}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
