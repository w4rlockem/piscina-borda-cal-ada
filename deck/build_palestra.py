"""Monta a apresentação de palestra: slides de tela cheia, em HTML.

Formato diferente da página de leitura. Aqui o alvo é projeção: fundo
escuro (sala com luz baixa), tipo grande o bastante para o fundo da sala,
imagem dominando o quadro e texto reduzido ao que se lê de longe.

A composição é autorada num palco fixo de 1280x720 e escalada por
transform para caber em qualquer projetor -- assim o enquadramento sai
idêntico em qualquer tela, sem reflow.
"""
import base64
import html
import io
import json
import os

from PIL import Image

import montagem as M
from gerar import SAIDA

DESTINO = M.caminho("deck/palestra.html")

# Paleta tirada das proprias fotos: o ciano e a agua da piscina, o fundo e
# o tom de ardosia molhada da sombra sobre a pedra.
CSS = """
:root{
  --fundo:#0d1a1f; --palco:#0d1a1f; --superficie:#16262c; --sup2:#1d3138;
  --tinta:#eef3f4; --meio:#a9c2ca; --fraco:#7c98a1;
  --agua:#3fb8d4; --alerta:#e8806d; --bom:#84c48f; --atencao:#e0b055;
  --serif:Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--fundo)}
body{color:var(--tinta);font-family:var(--sans);
  -webkit-font-smoothing:antialiased}
img{display:block;max-width:100%}

#palco{position:fixed;left:50%;top:50%;width:1280px;height:720px;
  transform-origin:center center;background:var(--palco)}
.slide{position:absolute;inset:0;padding:54px 64px;opacity:0;
  visibility:hidden;transition:opacity .28s ease}
.slide.on{opacity:1;visibility:visible}
@media (prefers-reduced-motion:reduce){.slide{transition:none}}

h1{font-family:var(--serif);font-size:52px;line-height:1.08;
  text-wrap:balance;font-weight:700}
h2{font-family:var(--serif);font-size:38px;line-height:1.12;
  text-wrap:balance;font-weight:700}
h3{font-family:var(--serif);font-size:23px;font-weight:700}
.olho{font-size:12px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--agua);font-weight:700;margin-bottom:14px}
.sub{font-size:19px;color:var(--meio);line-height:1.45;max-width:62ch}
.peq{font-size:14px;color:var(--fraco);line-height:1.4}
.num{font-family:var(--serif);font-size:60px;color:var(--agua);
  line-height:.9;font-weight:700}

/* capa ------------------------------------------------------------ */
.capa{padding:0}
.capa img{width:1280px;height:720px;object-fit:cover}
.capa .veu{position:absolute;inset:0;
  background:linear-gradient(90deg,rgba(9,20,25,.94) 0%,
    rgba(9,20,25,.86) 42%,rgba(9,20,25,.15) 78%)}
.capa .txt{position:absolute;left:64px;top:190px;width:660px}

/* grades ---------------------------------------------------------- */
.col2{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:start}
.col3{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.cartao{background:var(--superficie);border-radius:8px;padding:20px 22px}
.cartao h3{font-size:17px;font-family:var(--sans);margin-bottom:7px}
.cartao p{font-size:14px;color:var(--meio);line-height:1.45}
figure figcaption{font-size:13px;color:var(--fraco);margin-top:9px;
  font-style:italic}
.foto{border-radius:8px;overflow:hidden;background:var(--sup2)}

/* material -------------------------------------------------------- */
.cabeca{display:flex;justify-content:space-between;align-items:flex-start;
  margin-bottom:22px;gap:26px}
.preco{text-align:right;white-space:nowrap}
.preco b{font-size:24px;font-family:var(--serif)}
.preco span{display:block;font-size:12px;color:var(--fraco);margin-top:3px}
.criterio{display:flex;align-items:center;gap:12px;margin:9px 0;font-size:15px}
.criterio span:first-child{width:170px;color:var(--meio)}
.pip{width:22px;height:11px;border-radius:2px;background:#2b444d;
  display:inline-block;margin-right:4px}
.pip.on{background:var(--agua)}
.tag{display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;
  font-weight:700;color:#08161b}
.tag.sim{background:var(--bom)} .tag.limitado{background:var(--atencao)}
.tag.nao{background:var(--alerta)}
.aviso{background:var(--alerta);color:#2a0a05;border-radius:6px;
  padding:12px 16px;font-size:15px;font-weight:700;line-height:1.35}

/* tabela ---------------------------------------------------------- */
table{border-collapse:collapse;width:100%;font-size:14px;
  font-variant-numeric:tabular-nums}
th{background:var(--sup2);padding:10px 8px;font-size:12px;
  letter-spacing:.04em;text-transform:uppercase;color:var(--meio)}
th:nth-child(2){text-align:left}
td{padding:8px;text-align:center;border-bottom:1px solid #23383f}
td:nth-child(2){text-align:left;font-weight:600}
.n1,.n2{color:var(--alerta);font-weight:700}
.n4,.n5{color:var(--bom);font-weight:700}

/* comparador e cortina -------------------------------------------- */
.comp{display:grid;grid-template-columns:1fr 300px;gap:26px}
.tiras{display:flex;flex-direction:column;gap:5px}
.tira{display:flex;gap:10px;align-items:center;padding:7px 10px;border:0;
  border-radius:6px;background:transparent;color:var(--tinta);cursor:pointer;
  font:inherit;font-size:14px;text-align:left;width:100%}
.tira:hover{background:var(--superficie)}
.tira:focus-visible{outline:2px solid var(--agua);outline-offset:2px}
.tira[aria-pressed="true"]{background:var(--agua);color:#08161b;font-weight:700}
.tira .am{width:38px;height:26px;border-radius:3px;flex:none;
  background-size:cover;border:1px solid rgba(255,255,255,.18)}

/* Altura fixa, nao aspect-ratio: o palco tem 720 px e a imagem em
   proporcao cheia empurra legenda e rotulos para fora do slide. */
.cortina{position:relative;border-radius:8px;overflow:hidden;
  width:100%;height:436px;touch-action:none}
.cortina img{position:absolute;inset:0;width:100%;height:100%;
  object-fit:cover}
.cortina .depois{clip-path:inset(0 0 0 var(--corte,50%))}
.cortina .puxador{position:absolute;top:0;bottom:0;left:var(--corte,50%);
  width:3px;background:var(--agua);cursor:ew-resize}
.cortina .puxador::after{content:"";position:absolute;top:50%;left:50%;
  width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;
  background:var(--agua);box-shadow:0 3px 14px rgba(0,0,0,.5)}
.cortina .rot{position:absolute;bottom:14px;padding:5px 12px;border-radius:4px;
  background:rgba(8,20,25,.82);font-size:13px;font-weight:700}
.cortina .rot.esq{left:14px} .cortina .rot.dir{right:14px}

/* cromo ----------------------------------------------------------- */
#barra{position:fixed;left:0;bottom:0;height:3px;background:var(--agua);
  width:0;transition:width .28s ease;z-index:5}
#conta{position:fixed;right:16px;bottom:12px;font-size:12px;
  color:var(--fraco);z-index:5;font-variant-numeric:tabular-nums}
#ajuda{position:fixed;left:16px;bottom:12px;font-size:12px;
  color:var(--fraco);z-index:5}
#mapa{position:fixed;inset:0;background:rgba(7,16,20,.97);z-index:10;
  display:none;overflow:auto;padding:26px;grid-template-columns:repeat(6,1fr);
  gap:12px;align-content:start}
#mapa.on{display:grid}
#mapa button{border:2px solid transparent;border-radius:6px;padding:0;
  background:var(--superficie);cursor:pointer;color:var(--meio);
  font:inherit;font-size:11px;overflow:hidden;text-align:left}
#mapa button:hover,#mapa button:focus-visible{border-color:var(--agua);
  outline:none}
#mapa button i{display:block;padding:7px 9px;font-style:normal}
"""

JS = """
(function(){
  var palco=document.getElementById('palco'),
      slides=[].slice.call(document.querySelectorAll('.slide')),
      barra=document.getElementById('barra'),
      conta=document.getElementById('conta'),
      mapa=document.getElementById('mapa'),
      i=0;

  function ajusta(){
    var s=Math.min(innerWidth/1280, innerHeight/720);
    palco.style.transform='translate(-50%,-50%) scale('+s+')';
  }
  addEventListener('resize',ajusta); ajusta();

  function vai(n){
    i=Math.max(0,Math.min(slides.length-1,n));
    slides.forEach(function(s,j){ s.classList.toggle('on', j===i); });
    barra.style.width=((i+1)/slides.length*100)+'%';
    conta.textContent=(i+1)+' / '+slides.length;
    location.hash='s'+(i+1);
  }
  addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'||e.key==='n'){
      vai(i+1); e.preventDefault();
    } else if(e.key==='ArrowLeft'||e.key==='PageUp'||e.key==='p'){
      vai(i-1); e.preventDefault();
    } else if(e.key==='Home'){ vai(0); }
    else if(e.key==='End'){ vai(slides.length-1); }
    else if(e.key==='g'||e.key==='G'){ mapa.classList.toggle('on'); }
    else if(e.key==='Escape'){ mapa.classList.remove('on'); }
    else if(e.key==='f'||e.key==='F'){
      if(document.fullscreenElement){ document.exitFullscreen(); }
      else { document.documentElement.requestFullscreen(); }
    }
  });
  [].forEach.call(mapa.querySelectorAll('button'),function(b,j){
    b.addEventListener('click',function(){ mapa.classList.remove('on'); vai(j); });
  });

  // Avanco por clique. Necessario quando a apresentacao roda dentro de um
  // quadro: ate o primeiro clique o teclado nao chega na pagina. Ignora
  // cliques em elementos interativos, senao a cortina e o comparador
  // virariam botoes de proximo slide.
  palco.addEventListener('click',function(e){
    if(e.target.closest('button, .cortina, a, input')) return;
    vai(e.clientX < innerWidth*0.28 ? i-1 : i+1);
  });

  // Comparador de materiais de piso.
  var dados=JSON.parse(document.getElementById('dados').textContent),
      alvo=document.getElementById('comp-img'),
      rot=document.getElementById('comp-rot'),
      tiras=[].slice.call(document.querySelectorAll('.tira'));
  function escolhe(k){
    alvo.src=document.getElementById('mini-'+dados[k].id).src;
    rot.textContent=dados[k].nome+'  ·  R$ '+dados[k].preco+'/m²';
    tiras.forEach(function(t,j){
      t.setAttribute('aria-pressed', j===k?'true':'false');
    });
  }
  tiras.forEach(function(t,k){
    t.addEventListener('click',function(){ escolhe(k); });
  });
  if(tiras.length) escolhe(0);

  // Cortina antes/depois.
  // Cortina: os ouvintes de movimento ficam na janela, nao no elemento.
  // Com setPointerCapture no proprio elemento so o primeiro pointermove
  // chegava e a cortina travava logo no inicio do arrasto.
  var cort=document.getElementById('cortina');
  if(cort){
    var arrastando=false;
    function move(ev){
      var r=cort.getBoundingClientRect(),
          x=(ev.clientX-r.left)/r.width;
      cort.style.setProperty('--corte',(Math.max(0,Math.min(1,x))*100)+'%');
    }
    cort.addEventListener('pointerdown',function(e){
      arrastando=true; move(e); e.preventDefault();
    });
    addEventListener('pointermove',function(e){ if(arrastando) move(e); });
    addEventListener('pointerup',function(){ arrastando=false; });
    addEventListener('pointercancel',function(){ arrastando=false; });
  }

  var h=parseInt((location.hash||'').replace('#s',''),10);
  vai(isNaN(h)?0:h-1);
})();
"""


def b64(arquivo, largura=None, q=80):
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


def pips(nota, total=5):
    return "".join(f'<i class="pip{" on" if k < nota else ""}"></i>'
                   for k in range(total))


CRIT_PISO = [("aderencia", "Antiderrapante"), ("termico", "Não esquenta"),
             ("custo", "Custo baixo"), ("manutencao", "Baixa manutenção"),
             ("maresia", "Resiste à maresia")]
CRIT_BORDA = [("aderencia", "Antiderrapante"), ("termico", "Não esquenta"),
              ("cloro", "Resiste ao cloro"), ("sob_medida", "Peça sob medida"),
              ("custo", "Custo baixo")]
ROT_TAG = {"sim": "Serve", "limitado": "Limitado", "nao": "Não serve"}


def main():
    mats = M.carrega_materiais()
    bordas = M.carrega_bordas()
    por_id = {m["id"]: m for m in mats}
    slides, titulos = [], []

    def add(titulo, corpo, classe=""):
        slides.append(f'<section class="slide {classe}">{corpo}</section>')
        titulos.append(titulo)

    # 1 -------------------------------------------------------------
    add("Capa", f"""
      <img src="{b64('capa.jpg', 1400, 82)}" alt="A piscina e a casa ao fundo">
      <div class="veu"></div>
      <div class="txt">
        <div class="olho">Ponta da Fruta · Vila Velha — ES</div>
        <h1>Trocar a borda<br>e a calçada da piscina</h1>
        <p class="sub" style="margin-top:20px">Dez materiais aplicados sobre as
          fotos do próprio local — e o detalhe que decide se a obra dura.</p>
      </div>""", "capa")

    # 2 -------------------------------------------------------------
    add("O problema", f"""
      <div class="olho">O problema</div>
      <h2>O defeito não é o piso</h2>
      <div class="col2" style="margin-top:26px;grid-template-columns:1.15fr 1fr">
        <div class="foto"><img src="{b64('diagnostico.jpg', 820)}"
          alt="Close do canto com as marcações"></div>
        <div>
          <div class="cartao" style="margin-bottom:14px">
            <h3><span style="color:var(--alerta)">1</span> &nbsp;Não existe peça de borda</h3>
            <p>A casca de fibra termina e sobra concreto bruto até a pedra.
               Nunca houve acabamento ali.</p></div>
          <div class="cartao" style="margin-bottom:14px">
            <h3><span style="color:var(--alerta)">2</span> &nbsp;Rejunte largo, com mato</h3>
            <p>Degrada mais a percepção do que o desgaste da pedra.</p></div>
          <div class="cartao">
            <h3><span style="color:var(--alerta)">3</span> &nbsp;Duas paginações misturadas</h3>
            <p>Placa serrada na maior parte, caco irregular junto à piscina.</p></div>
        </div>
      </div>""")

    # 3 -------------------------------------------------------------
    add("A borda: antes e depois", f"""
      <div class="olho">A peça que falta</div>
      <h2>Arraste para ver o que muda</h2>
      <div class="cortina" id="cortina" style="margin-top:22px;--corte:50%">
        <img src="{b64('borda_antes.jpg', 1180)}" alt="Hoje: fibra exposta">
        <img class="depois" src="{b64('borda_b-granito-branco.jpg', 1180)}"
             alt="Com peça de borda em granito">
        <div class="puxador"></div>
        <div class="rot esq">Hoje — fibra exposta</div>
        <div class="rot dir">Com peça de borda</div>
      </div>
      <p class="peq" style="margin-top:14px">A peça avança 2–3 cm sobre a lâmina
        da fibra e a esconde. É a diferença entre piscina acabada e piscina
        montada.</p>""")

    # 4 -------------------------------------------------------------
    add("Perfis de borda", f"""
      <div class="olho">Como a peça é feita</div>
      <h2>Quatro perfis, um recomendado</h2>
      <div class="foto" style="margin-top:20px;background:#fff">
        <img src="{b64('perfis.png')}" alt="Os quatro perfis em corte"></div>
      <div class="col3" style="margin-top:20px">
        <div class="cartao"><h3>Junta flexível, nunca rejunte</h3>
          <p>A fibra trabalha com temperatura. Rejunte rígido nessa
             interface trinca — é o erro mais comum.</p></div>
        <div class="cartao"><h3>Pingadeira por baixo</h3>
          <p>Sem o sulco, a água escorre pela face da peça e mancha.</p></div>
        <div class="cartao"><h3>Caimento para fora</h3>
          <p>1 a 1,5%. Hoje a água suja da calçada volta para dentro.</p></div>
      </div>""")

    # 5 -------------------------------------------------------------
    add("Seis materiais de borda", f"""
      <div class="olho">A borda</div>
      <h2>Seis materiais para a peça de borda</h2>
      <p class="sub" style="margin-top:8px">Mesmo piso em todas as imagens.
        Só a borda muda.</p>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);
                  gap:16px;margin-top:20px">
        {''.join(f'''<figure><div class="foto"><img src="{b64(f"borda_{b['id']}.jpg", 400)}"
           alt="{e(b['nome'])}" style="height:172px;width:100%;object-fit:cover"></div>
           <figcaption style="color:var(--tinta);font-style:normal;
             font-weight:600;margin-top:7px">{b['n']}. {e(b['nome'])}</figcaption>
           <div class="peq">R$ {b['preco_ml'][0]}–{b['preco_ml'][1]} / m linear</div>
         </figure>''' for b in bordas)}
      </div>""")

    # 6..11 ---------------------------------------------------------
    for b in bordas:
        aviso = (f'<div class="aviso" style="margin-top:16px">▲ {e(b["alerta"])}</div>'
                 if b["alerta"] else "")
        add(f"Borda {b['n']}: {b['nome']}", f"""
          <div class="cabeca">
            <div style="display:flex;gap:20px;align-items:baseline">
              <div class="num">{b['n']}</div>
              <div><h2 style="font-size:32px">{e(b['nome'])}</h2>
                <p class="peq" style="margin-top:5px">{e(b['subtitulo'])}</p></div>
            </div>
            <div class="preco"><b>R$ {b['preco_ml'][0]}–{b['preco_ml'][1]}</b>
              <span>por metro linear · ~18 m no perímetro</span></div>
          </div>
          <div class="col2" style="grid-template-columns:1.35fr 1fr">
            <div class="foto"><img src="{b64(f"borda_{b['id']}.jpg", 700)}"
              alt="{e(b['nome'])} aplicado"></div>
            <div>
              <p style="font-size:17px;line-height:1.42">{e(b['resumo'])}</p>
              <div style="margin:18px 0">
                {''.join(f'<div class="criterio"><span>{e(r)}</span>'
                         f'<span>{pips(b["criterios"][k])}</span></div>'
                         for k, r in CRIT_BORDA)}
              </div>
              <div class="peq" style="color:var(--bom);font-weight:700">A FAVOR</div>
              <p class="peq" style="margin-bottom:10px">{e(b['a_favor'])}</p>
              <div class="peq" style="color:var(--alerta);font-weight:700">CONTRA</div>
              <p class="peq">{e(b['contra'])}</p>
              {aviso}
            </div>
          </div>""")

    # 12 ------------------------------------------------------------
    add("O piso", f"""
      <div class="olho">Segunda decisão</div>
      <h2>Agora o piso</h2>
      <p class="sub" style="margin-top:14px">A borda resolve o acabamento.
        O piso resolve os 60 a 75 m² em volta — e é onde se anda descalço
        no sol do meio-dia.</p>
      <div class="col3" style="margin-top:30px">
        <div class="cartao"><h3>Cinco quadrados é sempre o melhor</h3>
          <p>Inclusive em «custo baixo»: cinco quadrados quer dizer mais
             barato, não mais caro.</p></div>
        <div class="cartao"><h3>Borda e piso são independentes</h3>
          <p>Cada material diz se serve para borda, para piso, ou para
             os dois.</p></div>
        <div class="cartao"><h3>Litoral cobra caro</h3>
          <p>Ponta da Fruta é praia: maresia entra como critério em
             todos eles.</p></div>
      </div>""")

    # 13..22 --------------------------------------------------------
    for m in mats:
        aviso = (f'<div class="aviso" style="margin-top:14px">▲ {e(m["alerta"])}</div>'
                 if m["alerta"] else "")
        add(f"{m['n']}. {m['nome']}", f"""
          <div class="cabeca">
            <div style="display:flex;gap:20px;align-items:baseline">
              <div class="num">{m['n']:02d}</div>
              <div><h2 style="font-size:32px">{e(m['nome'])}</h2>
                <p class="peq" style="margin-top:5px">{e(m['familia'])} ·
                   {e(m['subtitulo'])}</p></div>
            </div>
            <div class="preco"><b>R$ {m['preco_m2'][0]}–{m['preco_m2'][1]}</b>
              <span>por m² instalado</span></div>
          </div>
          <div class="col2" style="grid-template-columns:1.35fr 1fr">
            <div class="foto"><img src="{b64(f"pano_{m['id']}.jpg", 700)}"
              alt="{e(m['nome'])} aplicado na área"></div>
            <div>
              <p style="font-size:17px;line-height:1.42">{e(m['resumo'])}</p>
              <div style="margin:16px 0">
                {''.join(f'<div class="criterio"><span>{e(r)}</span>'
                         f'<span>{pips(m["criterios"][k])}</span></div>'
                         for k, r in CRIT_PISO)}
              </div>
              <div style="display:flex;gap:22px;font-size:13px;
                          color:var(--meio);align-items:center">
                <span>Borda <span class="tag {m['borda']}">{ROT_TAG[m['borda']]}</span></span>
                <span>Piso <span class="tag {m['piso']}">{ROT_TAG[m['piso']]}</span></span>
              </div>
              {aviso}
            </div>
          </div>""")

    # 23 ------------------------------------------------------------
    ordem = sorted(mats, key=lambda m: sum(m["preco_m2"]) / 2)
    linhas = ""
    for m in ordem:
        cels = "".join(f'<td class="n{m["criterios"][k]}">{m["criterios"][k]}</td>'
                       for k, _ in CRIT_PISO)
        linhas += (f'<tr><td>{m["n"]}</td><td>{e(m["nome"])}</td>{cels}'
                   f'<td>{m["preco_m2"][0]}–{m["preco_m2"][1]}</td></tr>')
    add("Tabela", f"""
      <div class="olho">Os dez</div>
      <h2>Do mais barato ao mais caro</h2>
      <table style="margin-top:20px"><thead><tr><th>#</th><th>Material</th>
        {''.join(f'<th>{e(r)}</th>' for _, r in CRIT_PISO)}
        <th>R$/m²</th></tr></thead><tbody>{linhas}</tbody></table>""")

    # 24 ------------------------------------------------------------
    dados, tiras, ocultas = [], "", ""
    for k, m in enumerate(mats):
        dados.append({"id": m["id"], "nome": m["nome"],
                      "preco": f'{m["preco_m2"][0]}–{m["preco_m2"][1]}'})
        ocultas += (f'<img id="mini-{m["id"]}" src="{b64(f"mini_{m["id"]}.jpg", 760)}"'
                    f' alt="" hidden>')
        tiras += (f'<button class="tira" aria-pressed="false">'
                  f'<span class="am" style="background-image:url('
                  f'{b64(f"amostra_{m["id"]}.jpg", 110, 78)})"></span>'
                  f'<span>{m["n"]:02d} {e(m["nome"])}</span></button>')
    add("Comparador", f"""
      <div class="olho">Comparador</div>
      <h2>Qual você escolheria?</h2>
      <div class="comp" style="margin-top:18px">
        <div><div class="foto"><img id="comp-img" src="" alt="Montagem"
               style="width:100%;height:428px;object-fit:cover"></div>
          <p id="comp-rot" style="margin-top:10px;font-size:16px;
             font-weight:600"></p></div>
        <div class="tiras">{tiras}</div>
      </div>
      <div hidden>{ocultas}</div>""")

    # 25 ------------------------------------------------------------
    combos = [("equilibrio", "granito-branco-itaunas", "granito-branco-itaunas",
               "Equilíbrio", "Claro sem ferver, resistente sem impermeabilizar, "
               "barato pela proximidade de Cachoeiro."),
              ("conforto", "quartzito-branco-goias", "granito-branco-itaunas",
               "Conforto ao pé", "O piso mais frio da lista, com a borda em "
               "granito onde mais se pisa molhado."),
              ("manutencao", "porcelanato-pedra", "granito-cinza-andorinha",
               "Menor manutenção", "Não mancha, não cria limo, ignora maresia. "
               "Para não pensar na área de novo.")]
    add("Recomendação", f"""
      <div class="olho">Recomendação</div>
      <h2>Três combinações defensáveis</h2>
      <div class="col3" style="margin-top:20px">
        {''.join(f'''<div class="cartao" style="padding:0;overflow:hidden">
          <div class="foto" style="border-radius:0"><img
            src="{b64(f"combo_{s}.jpg", 400)}" alt="{e(rot)}"></div>
          <div style="padding:16px 18px">
            <h3 style="font-family:var(--serif);font-size:21px">{e(rot)}</h3>
            <p style="color:var(--agua);font-size:13px;font-weight:600;
                      margin:8px 0 8px">Piso {e(por_id[p]['nome'])}<br>
               Borda {e(por_id[bd]['nome'])}</p>
            <p style="font-size:13px;color:var(--meio);line-height:1.4">{e(txt)}</p>
          </div></div>''' for s, p, bd, rot, txt in combos)}
      </div>""")

    # 26 ------------------------------------------------------------
    add("Próximos passos", """
      <div class="olho">Antes de contratar</div>
      <h2>O que exigir de quem executar</h2>
      <div class="col3" style="margin-top:26px">
        <div class="cartao"><h3 style="color:var(--agua)">Confirmar no local</h3>
          <p>Medir piscina e calçada com trena. Conferir para onde a água
             corre hoje. Ver o contrapiso ao remover a primeira placa.</p></div>
        <div class="cartao"><h3 style="color:var(--bom)">Perguntar à marmoraria</h3>
          <p>Tem o lote em estoque? Faz peça boleada com pingadeira? Fornece
             amostra física de 20×20 do lote que será usado?</p></div>
        <div class="cartao"><h3 style="color:var(--alerta)">Exigir na obra</h3>
          <p>Junta flexível em mastique PU. Caimento conferido com nível.
             Rejunte epóxi. Juntas de dilatação a cada 3 m. Inox 316.</p></div>
      </div>
      <div style="margin-top:32px;background:var(--sup2);border-radius:8px;
                  padding:20px 24px">
        <p style="font-size:19px;font-weight:700">Peça amostra física e veja a
          placa sob o sol do local — molhada e seca — antes de fechar.</p>
        <p class="peq" style="margin-top:8px">As montagens são estudo de
          acabamento, não renderização fotorrealista. Cor de pedra natural
          varia por lote. Preços são faixas indicativas para a Grande
          Vitória/ES, a confirmar com fornecedor local.</p>
      </div>""")

    mapa = "".join(f'<button><i>{k + 1}. {e(t)}</i></button>'
                   for k, t in enumerate(titulos))

    doc = f"""<meta charset="utf-8">
<title>Piscina menor — borda e calçada</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div id="palco">{''.join(slides)}</div>
<div id="barra"></div>
<div id="conta"></div>
<div id="ajuda">← → navegar · G mapa · F tela cheia</div>
<div id="mapa">{mapa}</div>
<script type="application/json" id="dados">{json.dumps(dados)}</script>
<script>{JS}</script>
"""
    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"{DESTINO}  ({os.path.getsize(DESTINO) / 1e6:.1f} MB, "
          f"{len(slides)} slides)")


if __name__ == "__main__":
    main()
